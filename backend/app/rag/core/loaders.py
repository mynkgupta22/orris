from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import pandas as pd

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_community.document_loaders import PyMuPDFLoader
except ImportError:
    PyMuPDFLoader = None

from app.rag.core.schemas import DocumentChunk, ChunkMeta

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def detect_type(path: str) -> str:
    """Detect file type from extension."""
    ext = Path(path).suffix.lower()
    
    if ext == ".pdf":
        return "pdf"
    elif ext == ".docx":
        return "docx"
    elif ext in {".txt", ".log"}:
        return "txt"
    elif ext in {".xlsx", ".xls"}:
        return "xlsx"
    elif ext in IMAGE_EXTS:
        return "image"
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def _create_chunk(text: str, base_meta: Dict[str, Any], chunk_index: int, 
                 is_table: bool = False, is_image: bool = False, 
                 source_page: Optional[int] = None) -> DocumentChunk:
    """Create DocumentChunk directly."""
    # Simple token count estimate
    token_count = max(1, len(text) // 4) if text else 0
    
    meta = ChunkMeta(**{
        **base_meta,
        "chunk_id": str(uuid4()),
        "chunk_index": chunk_index,
        "is_table": is_table,
        "is_image": is_image,
        "source_page": source_page,
        "token_count": token_count,
        "ingested_at": datetime.utcnow(),
    })
    return DocumentChunk(text=text, meta=meta)


def load_pdf(path: str, base_meta: Dict[str, Any]) -> List[DocumentChunk]:
    """Load PDF and split into chunks."""
    if PyMuPDFLoader is None:
        raise RuntimeError("PyMuPDFLoader is required for PDF files")

    loader = PyMuPDFLoader(path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    chunks = []
    chunk_index = 0
    for idx, doc in enumerate(docs):
        text = getattr(doc, "page_content", "")
        if not text.strip():
            continue
            
        text_chunks = splitter.split_text(text)
        for chunk_text in text_chunks:
            if chunk_text.strip():
                chunks.append(_create_chunk(
                    text=chunk_text, base_meta=base_meta, 
                    chunk_index=chunk_index, source_page=idx + 1
                ))
                chunk_index += 1
    return chunks


def load_docx(path: str, base_meta: Dict[str, Any]) -> List[DocumentChunk]:
    """Load DOCX file and split into chunks."""
    try:
        from docx import Document
        doc = Document(path)
        text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        # Fallback to plain text
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    
    if not text.strip():
        return []
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    text_chunks = splitter.split_text(text)
    
    chunks = []
    for i, chunk_text in enumerate(text_chunks):
        if chunk_text.strip():
            chunks.append(_create_chunk(
                text=chunk_text, base_meta=base_meta, chunk_index=i
            ))
    return chunks


def load_txt(path: str, base_meta: Dict[str, Any]) -> List[DocumentChunk]:
    """Load text file and split into chunks."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = Path(path).read_text(encoding="latin-1")

    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    text_chunks = splitter.split_text(text)
    
    chunks = []
    for i, chunk_text in enumerate(text_chunks):
        if chunk_text.strip():
            chunks.append(_create_chunk(
                text=chunk_text, base_meta=base_meta, chunk_index=i
            ))
    return chunks


def load_xlsx(path: str, base_meta: Dict[str, Any]) -> List[DocumentChunk]:
    """Load Excel file and split into chunks."""
    sheets = pd.read_excel(path, sheet_name=None)
    chunks = []
    chunk_index = 0
    
    for sheet_name, df in sheets.items():
        if df.empty:
            continue
            
        # Split into 10-row chunks
        for start in range(0, len(df), 10):
            chunk_df = df.iloc[start:start + 10]
            text = f"Sheet: {sheet_name}\n{chunk_df.to_csv(index=False)}"
            
            # Add sheet_name to base_meta for this chunk
            meta_with_sheet = dict(base_meta)
            meta_with_sheet["sheet_name"] = sheet_name
            
            chunks.append(_create_chunk(
                text=text, base_meta=meta_with_sheet, 
                chunk_index=chunk_index, is_table=True
            ))
            chunk_index += 1
    
    return chunks


def load_image(path: str, base_meta: Dict[str, Any], 
               summarize_fn: Optional[Callable[[str], str]] = None) -> List[DocumentChunk]:
    """Load image file."""
    name = Path(path).name
    
    # Try to get summary if function provided
    if summarize_fn:
        try:
            text = summarize_fn(path)
        except Exception:
            text = f"Image: {name}"
    else:
        text = f"Image: {name}"
    
    # Add image_url to base_meta
    meta_with_image = dict(base_meta)
    meta_with_image["image_url"] = str(Path(path))
    meta_with_image["image_summary"] = text
    
    chunk = _create_chunk(
        text=text, base_meta=meta_with_image, 
        chunk_index=0, is_image=True
    )
    return [chunk]


def load_file_to_chunks(path: str, base_meta: Dict[str, Any], 
                       summarize_image_fn: Optional[Callable[[str], str]] = None) -> List[DocumentChunk]:
    """Load file and return DocumentChunk objects."""
    file_type = detect_type(path)
    
    if file_type == "pdf":
        return load_pdf(path, base_meta)
    elif file_type == "docx":
        return load_docx(path, base_meta)
    elif file_type == "txt":
        return load_txt(path, base_meta)
    elif file_type == "xlsx":
        return load_xlsx(path, base_meta)
    elif file_type == "image":
        return load_image(path, base_meta, summarize_image_fn)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# Backward compatibility
load_file_to_elements = load_file_to_chunks


