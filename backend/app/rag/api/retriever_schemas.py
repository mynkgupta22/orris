from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class QueryRequest(BaseModel):
    """Request model for retrieval queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    session_id: Optional[UUID] = Field(None, description="Chat session ID for multi-turn conversation")
    top_k_pre: Optional[int] = Field(30, ge=1, le=100, description="Number of candidates to retrieve before reranking")
    top_k_post: Optional[int] = Field(7, ge=1, le=20, description="Number of final results after reranking")

class APIQueryResponse(BaseModel):
    """Final, lean response model for the API"""
    answer: str
    query: str
    session_id: UUID
    image_base64: Optional[str] = None

class RetrievedChunk(BaseModel):
    """Detailed chunk model for internal use"""
    id: str
    text: str
    score: float
    payload: Dict[str, Any]

class DocumentChunk(BaseModel):
    """Document chunk with metadata"""
    id: str
    text: str
    score: float
    source_doc_name: str
    source_doc_id: str
    doc_type: str
    source_page: int
    chunk_index: int
    is_pi: bool
    uid: Optional[str] = None
    created_at: str
    doc_url: str
