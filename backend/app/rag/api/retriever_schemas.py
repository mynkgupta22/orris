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
    
class QueryResponse(BaseModel):
    """Response model for retrieval queries (minimal)"""
    answer: str
    query: str
    session_id: UUID

class AuditLog(BaseModel):
    """Audit log entry for queries"""
    audit_id: str
    user_id: str
    user_role: str
    query: str
    num_chunks_returned: int
    chunks_accessed: List[str]  # chunk IDs
    processing_time_ms: int
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class SearchFilter(BaseModel):
    """Internal model for search filters"""
    is_pi: Optional[bool] = None
    uid: Optional[str] = None
    doc_type: Optional[str] = None
    source_doc_name: Optional[str] = None