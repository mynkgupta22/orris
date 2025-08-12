from __future__ import annotations

import httplib2
from dataclasses import dataclass
from typing import Dict, Generator, Iterable, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import io
import os
import logging  


from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__) 

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


# def get_drive_service() -> any:
#     """Create a Google Drive API client using a service account file.

#     Environment variables:
#       - GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_FILE: path to JSON
#       - GOOGLE_DRIVE_SCOPES (optional, comma-separated)
#     """
#     cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv(
#         "GOOGLE_SERVICE_ACCOUNT_FILE"
#     )
#     if not cred_path:
#         raise RuntimeError(
#             "Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_FILE to your service account JSON."
#         )
#     scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
#     scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
#     creds = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
#     return build("drive", "v3", credentials=creds, cache_discovery=False)

# In file: app/rag/integrations/drive.py

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- This is the function you must replace ---

# def get_drive_service() -> any:
#     """
#     Creates a Google Drive service client by securely loading credentials
#     directly from an environment variable containing the JSON content.

#     Environment variables:
#       - GOOGLE_APPLICATION_CREDENTIALS_JSON: The full JSON content of the service account.
#       - GOOGLE_DRIVE_SCOPES (optional, comma-separated)
#     """

#     logger.info("Attempting to create Google Drive service from environment variable content.")
#     # 1. Get the JSON content string from the environment variable.
#     #    We use a specific name to make it clear we expect content, not a path.
#     creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

#     # 2. Check if the variable exists and raise a clear error if it doesn't.
#     if not creds_json_str:
#         # This error will appear in your Render logs if the variable is missing.
#         raise ValueError("FATAL: The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")
#     else:
#         # Log the first 50 characters to confirm it's not empty without printing the whole secret
#         logger.info(f"Found GOOGLE_APPLICATION_CREDENTIALS_JSON variable, starts with: {creds_json_str[:50]}...")

#     try:
#         # 3. Load the JSON string into a Python dictionary.
#         creds_info = json.loads(creds_json_str)

#         # 4. Load scopes from environment or use default.
#         scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
#         scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES

#         # 5. Use the special 'from_service_account_info' method to create credentials.
#         credentials = service_account.Credentials.from_service_account_info(
#             creds_info, scopes=scopes
#         )

#         # 6. Build and return the Google Drive service object.
#         service = build("drive", "v3", credentials=credentials, cache_discovery=False)
#         logger.info("Successfully created Google Drive service object.")

#         return service

#     except json.JSONDecodeError:
#         # This error will appear if the pasted JSON is invalid.
#         raise ValueError("FATAL: The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable contains invalid JSON.")
#     except Exception as e:
#         # Log any other errors during service creation.
#         logger.error(f"Failed to create Google Drive service: {e}") # You might need to import logger
#         raise

def get_drive_service() -> any:
    """
    Creates a Google Drive service client by securely loading credentials
    from an environment variable and explicitly disabling all file-based caching.
    """
    logger.info("Attempting to create Google Drive service from environment variable content.")
    creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if not creds_json_str:
        raise ValueError("FATAL: The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")

    try:
        creds_info = json.loads(creds_json_str)
        scopes_env = os.getenv("GOOGLE_DRIVE_SCOPES")
        scopes = [s.strip() for s in scopes_env.split(",")] if scopes_env else DEFAULT_SCOPES
        credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)

        # --- THIS IS THE CRITICAL FIX ---
        # 1. Create a new Http object with all caching disabled.
        http_client = httplib2.Http(cache=None)
        # 2. Authorize this specific client instance with our credentials.
        credentials.authorize(http_client)
        # 3. Build the service using this custom, cacheless Http object.
        service = build("drive", "v3", http=http_client, cache_discovery=False)
        # --- END OF FIX ---

        logger.info("Successfully created Google Drive service object.")
        return service

    except Exception as e:
        logger.error(f"Failed to create Google Drive service: {e}")
        raise

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


