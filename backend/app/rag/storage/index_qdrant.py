from __future__ import annotations

from typing import Iterable, List, Optional, Dict, Any
import os

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.rag.config.config import load_qdrant_config
from app.rag.core.schemas import DocumentChunk
from app.rag.core.embed import EmbeddingClient, get_embedding_client


def get_client() -> QdrantClient:
    cfg = load_qdrant_config()
    return QdrantClient(host=cfg.host, port=cfg.port, api_key=cfg.api_key)


def ensure_collection(client: QdrantClient, vector_size: int, *, force: bool = False) -> str:
    """Ensure the target collection exists with a named vector 'text'.

    Returns the collection name.
    """
    cfg = load_qdrant_config()
    name = cfg.collection_name
    try:
        exists = client.get_collection(collection_name=name)
        if force:
            # Recreate if forced
            client.recreate_collection(
                collection_name=name,
                vectors_config={
                    "text": VectorParams(size=vector_size, distance=Distance.COSINE)
                },
            )
        else:
            # If exists and not forced, we are done
            _ = exists  # touch to avoid linter
    except Exception:
        # Create if it doesn't exist
        client.create_collection(
            collection_name=name,
            vectors_config={
                "text": VectorParams(size=vector_size, distance=Distance.COSINE)
            },
        )
    return name


def _to_point(chunk: DocumentChunk, vector: List[float]) -> PointStruct:
    return PointStruct(
        id=chunk.meta.chunk_id,
        vector={"text": vector},
        payload=chunk.meta.model_dump(),
    )


def upsert_document_chunks(
    chunks: Iterable[DocumentChunk],
    *,
    embedding: Optional[EmbeddingClient] = None,
    batch_size: int = 64,
) -> int:
    """Embed and upsert chunks into Qdrant. Returns number of points written.

    This function loads Qdrant config from the environment and ensures the
    collection exists with the correct vector size.
    """
    emb = embedding or get_embedding_client()
    client = get_client()
    collection = ensure_collection(client, vector_size=emb.dimension)

    # Materialize list to batch
    chunk_list: List[DocumentChunk] = list(chunks)
    written = 0
    for i in range(0, len(chunk_list), batch_size):
        batch = chunk_list[i : i + batch_size]
        texts = [c.text for c in batch]
        vecs = emb.encode_texts(texts)
        # Build points with named vector
        points: List[PointStruct] = []
        for j in range(len(batch)):
            # Fill small metadata adds at index time
            meta = batch[j].meta
            payload = meta.model_dump()
            payload.setdefault("embedding_model", emb.model_name)
            payload.setdefault("embedding_dim", emb.dimension)
            payload.setdefault("pipeline_version", os.getenv("PIPELINE_VERSION", "0.1.0"))
            payload["text"] = batch[j].text  # ensure text is retrievable
            payload.setdefault("doc_url", payload.get("source_doc_url"))  # alias for retrieval
            payload.setdefault("created_at", payload.get("ingested_at")) 
            points.append(
                PointStruct(
                    id=meta.chunk_id,
                    vector={"text": vecs[j].tolist()},
                    payload=payload,
                )
            )
        client.upsert(collection_name=collection, points=points)
        written += len(points)
    return written


def build_filter(eq: Optional[Dict[str, Any]] = None) -> Optional[Filter]:
    """Build a simple equality filter from a dict of key -> value.

    For advanced logic (should/must), extend this function later.
    """
    if not eq:
        return None
    conditions = []
    for key, value in eq.items():
        conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
    return Filter(must=conditions)


def delete_document_chunks(source_doc_id: str) -> int:
    """Delete all chunks belonging to a specific document from Qdrant.
    
    Args:
        source_doc_id: The Google Drive file ID or document identifier
        
    Returns:
        Number of chunks deleted
    """
    client = get_client()
    collection = load_qdrant_config().collection_name
    
    # Build filter for the specific document
    doc_filter = build_filter({"source_doc_id": source_doc_id})
    
    # First, get all points for this document to count them
    search_result = client.scroll(
        collection_name=collection,
        scroll_filter=doc_filter,
        limit=10000,  # Large limit to get all chunks for the document
        with_payload=False,
        with_vectors=False
    )
    
    points_to_delete = [point.id for point in search_result[0]]
    
    if not points_to_delete:
        return 0
    
    # Delete points by IDs
    client.delete(
        collection_name=collection,
        points_selector=points_to_delete
    )
    
    return len(points_to_delete)


def search_text(
    query: str,
    top_k: int = 10,
    *,
    embedding: Optional[EmbeddingClient] = None,
    eq_filter: Optional[Dict[str, Any]] = None,
    with_vectors: bool = False,
):
    """Embed query and run a vector search against the named 'text' vector."""
    emb = embedding or get_embedding_client()
    client = get_client()
    collection = load_qdrant_config().collection_name

    qvec = emb.encode_texts([query])[0]
    flt = build_filter(eq_filter)
    return client.search(
        collection_name=collection,
        query_vector=("text", qvec.tolist()),
        limit=top_k,
        with_payload=True,
        with_vectors=with_vectors,
        query_filter=flt,
    )


