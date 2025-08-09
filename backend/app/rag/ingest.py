from __future__ import annotations

import os
import mimetypes
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List
from schemas import DocumentChunk, ChunkMeta
from loaders import load_file_to_elements
from chunking import chunk_elements
from index_qdrant import upsert_document_chunks
from drive import get_drive_service, walk_from_root, download_file, resolve_type_from_mime, classify_from_path
from extractors import extract_pdf_images, extract_docx_images

try:
    from vision import summarize_image_llava
except Exception:
    summarize_image_llava = None  # type: ignore


def build_base_meta(path: Path, *, is_pi: bool = False, uid: str | None = None) -> Dict[str, Any]:
    """Construct minimal base metadata for the file.

    In real usage, these come from Google Drive. Here we infer from path for MVP.
    """
    source_doc_type = _ext_to_type(path.suffix.lower())
    mime_type, _ = mimetypes.guess_type(str(path))
    return {
        "source_doc_id": path.stem,  # placeholder
        "source_doc_name": path.name,
        "source_doc_type": source_doc_type,
        "source_doc_url": None,
        "doc_mime_type": mime_type,
        "owner_uid": uid,
        "uid": uid,
        "roles_allowed": ["pi"] if is_pi else ["non_pi"],
        "is_pi": is_pi,
        "folder_path": str(path.parent),
        "source_last_modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        "ingested_at": datetime.now(UTC),
        "language": "en",
    }


def _ext_to_type(ext: str) -> str:
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in {".txt", ".log"}:
        return "txt"
    if ext in {".xlsx", ".xls"}:
        return "xlsx"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return "image"
    return ext.strip(".")


def main() -> None:
    # Source selection via environment variables
    gdrive_root_id = os.getenv("GDRIVE_ROOT_ID")
    local_path = os.getenv("INGEST_LOCAL_PATH")
    use_vision = os.getenv("USE_VISION", "false").lower() in {"1", "true", "yes"}
    tmp_dir = os.getenv("INGEST_TMP_DIR", ".ingest_tmp")

    summarize_fn = summarize_image_llava if (use_vision and summarize_image_llava is not None) else None

    num_files = 0
    total_elements = 0
    total_chunks = 0
    all_chunks: List[DocumentChunk] = []

    if gdrive_root_id:
        service = get_drive_service()
        tmp_root = Path(tmp_dir)
        tmp_root.mkdir(parents=True, exist_ok=True)

        for f in walk_from_root(service, gdrive_root_id):
            dtype = resolve_type_from_mime(f.name, f.mime_type)
            if dtype is None:
                continue
            num_files += 1
            # Classify PI/NON PI from logical path
            is_pi, uid, roles = classify_from_path(f.path_segments)
            # Download to temp path
            dest = tmp_root / "/".join([*f.path_segments, f.name])
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                download_file(service, f.id, dest)
            except Exception as e:
                print(f"[WARN] Download failed {f.name}: {e}")
                continue
            base_meta = {
                "source_doc_id": f.id,
                "source_doc_name": f.name,
                "source_doc_type": dtype,
                "source_doc_url": f.web_view_link,
                "doc_mime_type": f.mime_type,
                "owner_uid": uid,
                "uid": uid,
                "roles_allowed": roles,
                "is_pi": is_pi,
                "folder_path": "/".join(f.path_segments),
                "source_last_modified_at": f.modified_time,
                "ingested_at": datetime.now(UTC),
                "language": "en",
            }
            # Optional: extract images for PDFs and DOCX
            image_lookup = None
            if dtype == "pdf":
                extracted_dir = Path(tmp_dir) / "_images" / f.id
                page_map = extract_pdf_images(str(dest), str(extracted_dir))

                def _lookup(page_no: int):
                    return page_map.get(page_no, [])

                image_lookup = _lookup
            elif dtype == "docx":
                extracted_dir = Path(tmp_dir) / "_images" / f.id
                img_paths = extract_docx_images(str(dest), str(extracted_dir))
                # naive: map all images to page 1 (DOCX lacks native pages)
                def _lookup(_: int):
                    return img_paths

                image_lookup = _lookup

            try:
                elements = load_file_to_elements(str(dest), base_meta, summarize_image_fn=summarize_fn, image_lookup=image_lookup)
            except Exception as e:
                print(f"[WARN] Skipping {f.name}: {e}")
                continue
            total_elements += len(elements)
            chunks = chunk_elements(elements)
            total_chunks += len(chunks)
            all_chunks.extend(chunks)
    elif local_path:
        root = Path(local_path)
        assert root.exists() and root.is_dir(), f"Path does not exist or not a directory: {root}"
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            num_files += 1
            base_meta = build_base_meta(p)
            # Optional: extract images for PDFs and DOCX locally as well
            image_lookup = None
            dtype_local = _ext_to_type(p.suffix.lower())
            if dtype_local == "pdf":
                extracted_dir = Path(tmp_dir) / "_images" / p.stem
                page_map = extract_pdf_images(str(p), str(extracted_dir))

                def _lookup(page_no: int):
                    return page_map.get(page_no, [])

                image_lookup = _lookup
            elif dtype_local == "docx":
                extracted_dir = Path(tmp_dir) / "_images" / p.stem
                img_paths = extract_docx_images(str(p), str(extracted_dir))

                def _lookup(_: int):
                    return img_paths

                image_lookup = _lookup
            try:
                elements = load_file_to_elements(str(p), base_meta, summarize_image_fn=summarize_fn, image_lookup=image_lookup)
            except Exception as e:
                print(f"[WARN] Skipping {p}: {e}")
                continue
            total_elements += len(elements)
            chunks = chunk_elements(elements)
            total_chunks += len(chunks)
            all_chunks.extend(chunks)
    else:
        raise RuntimeError("Set either GDRIVE_ROOT_ID or INGEST_LOCAL_PATH in environment.")

    if not all_chunks:
        print("No chunks to index. Exiting.")
        return

    written = upsert_document_chunks(all_chunks)

    print(
        f"Ingestion complete: files={num_files}, elements={total_elements}, chunks={total_chunks}, indexed={written}"
    )


if __name__ == "__main__":
    main()


