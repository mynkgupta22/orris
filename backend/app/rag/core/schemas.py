from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkMeta(BaseModel):
    """Minimal metadata schema aligned with metadata.md and MVP needs.

    This is intentionally small for the first phase and can be extended later.
    """

    # Identity / provenance
    chunk_id: str
    source_doc_id: str
    source_doc_name: str
    source_doc_type: str  # "pdf" | "docx" | "txt" | "xlsx" | "image"
    source_doc_url: Optional[str] = None
    doc_mime_type: Optional[str] = None

    # Ownership / access
    owner_uid: Optional[str] = None
    uid: Optional[str] = None
    roles_allowed: List[str] = Field(default_factory=list)
    is_pi: bool = False
    folder_path: Optional[str] = None
    # Last modified time from the source system (e.g., Google Drive)
    source_last_modified_at: Optional[datetime] = None

    # Processing info
    ingested_at: datetime
    chunk_index: int = 0
    source_page: Optional[int] = None
    language: str = "en"
    token_count: Optional[int] = None

    # Content flags
    is_table: bool = False
    is_image: bool = False
    image_summary: Optional[str] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None  # Base64 encoding of the image
    thumbnail_url: Optional[str] = None
    # Spreadsheet context (optional)
    sheet_name: Optional[str] = None


class DocumentChunk(BaseModel):
    """A normalized chunk ready for embedding/indexing."""

    text: str
    meta: ChunkMeta


