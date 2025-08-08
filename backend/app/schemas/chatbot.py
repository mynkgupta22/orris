from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    query: str
    context: Optional[str] = None


class DocumentInfo(BaseModel):
    id: str
    name: str
    is_pi_restricted: bool
    excerpt: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    documents_used: List[DocumentInfo]
    access_denied: bool = False
    access_denied_reason: Optional[str] = None
    processing_time_ms: int


class ChatAuditResponse(BaseModel):
    id: int
    query: str
    response: Optional[str]
    documents_accessed: Optional[str]
    access_denied: bool
    access_denied_reason: Optional[str]
    processing_time_ms: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentSearchRequest(BaseModel):
    query: str
    include_pi_restricted: bool = False


class DocumentSearchResponse(BaseModel):
    documents: List[DocumentInfo]
    total_count: int
    filtered_count: int