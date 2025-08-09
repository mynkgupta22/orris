from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover
    tiktoken = None  # type: ignore

try:
    # Preferred in latest LangChain releases (modularized package)
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
except Exception:  # fallback for older installations
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

from schemas import DocumentChunk, ChunkMeta


def _estimate_token_count(text: str) -> int:
    """Rough token estimate for metadata; best-effort fallback if tiktoken is unavailable."""
    if not text:
        return 0
    if tiktoken is None:
        # Heuristic: ~4 chars per token average
        return max(1, len(text) // 4)
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        return max(1, len(text) // 4)
    return len(enc.encode(text))


def chunk_elements(
    elements: List[Dict[str, Any]],
) -> List[DocumentChunk]:
    """Convert normalized elements from loaders into DocumentChunk objects.
    
    Elements are already chunked by unstructured, so we just convert format.
    """
    
    chunks: List[DocumentChunk] = []
    running_index = 0

    for el in elements:
        text: str = el.get("text") or ""
        meta_dict: Dict[str, Any] = dict(el.get("meta") or {})

        if not text.strip():
            continue

        meta = ChunkMeta(**{
            **meta_dict,
            "chunk_id": str(uuid4()),
            "chunk_index": running_index,
            "token_count": _estimate_token_count(text),
        })
        chunks.append(DocumentChunk(text=text, meta=meta))
        running_index += 1

    return chunks


