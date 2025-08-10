from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_history.session_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Core logging data for compliance
    user_query = Column(Text, nullable=False)  # Original user input
    llm_prompt = Column(Text, nullable=False)  # Complete prompt sent to LLM
    llm_response = Column(Text, nullable=False)  # Raw LLM response
    
    # Retrieved context for compliance
    retrieved_chunks = Column(JSONB, nullable=True)  # Document chunks used for context
    context_metadata = Column(JSONB, nullable=True)  # Additional context info
    
    # Performance and system data
    processing_time_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User")
    chat_session = relationship("ChatHistory", back_populates="query_logs")
    
    @classmethod
    def create_log(
        cls,
        user_id: int,
        user_query: str,
        llm_prompt: str,
        llm_response: str,
        processing_time_ms: int,
        session_id: uuid.UUID = None,
        retrieved_chunks: list = None,
        context_metadata: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        error_message: str = None,
        error_type: str = None
    ):
        """Factory method to create a query log entry"""
        return cls(
            user_id=user_id,
            session_id=session_id,
            user_query=user_query,
            llm_prompt=llm_prompt,
            llm_response=llm_response,
            retrieved_chunks=retrieved_chunks,
            context_metadata=context_metadata,
            processing_time_ms=processing_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            error_type=error_type
        )