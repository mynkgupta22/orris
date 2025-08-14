from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Generator, Iterable, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import io
import os
import json
import certifi
import httplib2

# Configure SSL certificates for Google API calls
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

# Patch httplib2 to use certifi by default
def patch_httplib2_ssl():
    """Patch httplib2 to use certifi certificates by default"""
    original_init = httplib2.Http.__init__
    
    def patched_init(self, cache=None, timeout=None, proxy_info=None, ca_certs=None, 
                     disable_ssl_certificate_validation=False, tls_maximum_version=None, 
                     tls_minimum_version=None):
        # If no ca_certs specified, use certifi
        if ca_certs is None:
            ca_certs = certifi.where()
        return original_init(self, cache=cache, timeout=timeout, proxy_info=proxy_info,
                           ca_certs=ca_certs, 
                           disable_ssl_certificate_validation=disable_ssl_certificate_validation,
                           tls_maximum_version=tls_maximum_version, 
                           tls_minimum_version=tls_minimum_version)
    
    httplib2.Http.__init__ = patched_init

# Apply the patch
patch_httplib2_ssl()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@dataclass
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: datetime
    parents: List[str]
    web_view_link: Optional[str]
    path_segments: List[str]  # logical path from provided root


def get_drive_service() -> any:
    """Create a Google Drive API client using service account credentials.

    Supports two modes:
    1. Local Development: Load from service account JSON file
    2. Production: Load from environment variable containing JSON data
    
    Environment variables:
      - GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS_JSON: JSON string containing service account data (production)
      - GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_FILE: path to JSON file (local)
      - GOOGLE_DRIVE_SCOPES (optional, comma-separated)
    """
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check for JSON data in environment variable first (production mode)
    # Support multiple environment variable names for flexibility
    service_account_json = (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    )
    
    if service_account_json:
        # Production mode: load from environment variable
        try:
            logger.info("Loading Google Drive credentials from environment variable")
            service_account_info = json.loads(service_account_json)
            scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
            scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
            creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
            logger.info("Successfully created Google Drive service from environment credentials")
            
            # Use credentials with proper SSL configuration via environment variables
            return build("drive", "v3", credentials=creds, cache_discovery=False)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create credentials from environment variable: {e}")
    
    # Local development mode: load from file
    logger.info("No environment credentials found, trying file-based credentials")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    
    if not cred_path:
        # Try default local paths
        from app.core.paths import SERVICE_ACCOUNT_PATH
        if SERVICE_ACCOUNT_PATH.exists():
            cred_path = str(SERVICE_ACCOUNT_PATH)
            logger.info(f"Using default service account file: {cred_path}")
        else:
            available_env_vars = [
                "GOOGLE_SERVICE_ACCOUNT_JSON", 
                "GOOGLE_APPLICATION_CREDENTIALS_JSON",
                "GOOGLE_APPLICATION_CREDENTIALS", 
                "GOOGLE_SERVICE_ACCOUNT_FILE"
            ]
            raise RuntimeError(
                f"Google Drive credentials not found. For production, set one of: {available_env_vars[:2]}. "
                f"For local development, set one of: {available_env_vars[2:]} "
                f"or place service-account.json at {SERVICE_ACCOUNT_PATH}"
            )
    
    try:
        logger.info(f"Loading Google Drive credentials from file: {cred_path}")
        scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
        scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
        creds = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
        logger.info("Successfully created Google Drive service from file credentials")
        
        # Use credentials with proper SSL configuration via environment variables
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        raise RuntimeError(f"Failed to create credentials from file {cred_path}: {e}")


def _list_children(service, folder_id: str) -> List[dict]:
    q = f"'{folder_id}' in parents and trashed=false"
    fields = "nextPageToken, files(id, name, mimeType, parents, modifiedTime, webViewLink)"
    result: List[dict] = []
    page_token = None
    while True:
        resp = (
            service.files()
            .list(q=q, fields=fields, pageSize=1000, pageToken=page_token)
            .execute()
        )
        result.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return result


def walk_from_root(
    service,
    root_folder_id: str,
) -> Generator[DriveFile, None, None]:
    """Depth-first traversal yielding files (not folders) with logical path segments.

    The path is constructed from the root down to the file's immediate folder chain.
    """
    stack: List[Tuple[str, List[str]]] = [(root_folder_id, [])]
    while stack:
        folder_id, segments = stack.pop()
        children = _list_children(service, folder_id)
        for item in children:
            mime = item.get("mimeType")
            if mime == "application/vnd.google-apps.folder":
                stack.append((item["id"], segments + [item["name"]]))
                continue
            # file
            yield DriveFile(
                id=item["id"],
                name=item["name"],
                mime_type=mime,
                modified_time=datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00")),
                parents=item.get("parents", []),
                web_view_link=item.get("webViewLink"),
                path_segments=segments,
            )


SUPPORTED_MIME_PREFIXES = ("image/",)
SUPPORTED_MIME_EXACT = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


def resolve_type_from_mime(name: str, mime_type: str) -> Optional[str]:
    if mime_type in SUPPORTED_MIME_EXACT:
        return SUPPORTED_MIME_EXACT[mime_type]
    if any(mime_type.startswith(p) for p in SUPPORTED_MIME_PREFIXES):
        # validate by extension to be safe
        ext = Path(name).suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
            return "image"
    return None


def download_file(service, file_id: str, dest_path: Path) -> None:
    req = service.files().get_media(fileId=file_id)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            # Optional: print(f"Download {int(status.progress() * 100)}%")


def classify_from_path(path_segments: List[str]) -> tuple[bool, Optional[str], List[str]]:
    """Return (is_pi, uid, roles_allowed) based on path per Instructions.md.

    Expected structure under root: EVIDEV_DATA/{PI|NON PI}/...
    If under PI/<uid>/..., mark PI with uid; Otherwise NON PI.
    """
    is_pi = False
    uid: Optional[str] = None
    roles = ["non_pi"]
    if not path_segments:
        return is_pi, uid, roles
    first = path_segments[0].strip().lower()
    if first == "pi" and len(path_segments) >= 2:
        is_pi = True
        uid = path_segments[1]
        roles = ["pi"]
    return is_pi, uid, roles

