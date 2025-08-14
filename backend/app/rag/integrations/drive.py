from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Generator, Iterable, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import io
import os
import json

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
      - GOOGLE_SERVICE_ACCOUNT_JSON: JSON string containing service account data (production)
      - GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_FILE: path to JSON file (local)
      - GOOGLE_DRIVE_SCOPES (optional, comma-separated)
    """
    import json
    
    # Check for JSON data in environment variable first (production mode)
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if service_account_json:
        # Production mode: load from environment variable
        try:
            service_account_info = json.loads(service_account_json)
            scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
            scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
            creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
            return build("drive", "v3", credentials=creds, cache_discovery=False)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON environment variable: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create credentials from GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    
    # Local development mode: load from file
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    
    if not cred_path:
        # Try default local paths
        from app.core.paths import SERVICE_ACCOUNT_PATH
        if SERVICE_ACCOUNT_PATH.exists():
            cred_path = str(SERVICE_ACCOUNT_PATH)
        else:
            raise RuntimeError(
                "Google Drive credentials not found. For production, set GOOGLE_SERVICE_ACCOUNT_JSON. "
                "For local development, set GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_SERVICE_ACCOUNT_FILE, "
                f"or place service-account.json at {SERVICE_ACCOUNT_PATH}"
            )
    
    try:
        scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
        scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
        creds = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
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


