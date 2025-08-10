from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
import uuid

from app.core.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid.uuid4)
    title = Column(String(50), nullable=False)  # First 50 chars of first question
    conversation_data = Column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)  # Stores messages array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 30 days from creation
    
    # Relationships
    user = relationship("User", back_populates="chat_histories")
    query_logs = relationship("QueryLog", back_populates="chat_session", cascade="all, delete-orphan")
    
    def add_message(self, role: str, content: str, timestamp: str = None):
        """Add a message to the conversation"""
        if timestamp is None:
            timestamp = func.now()
            
        if not self.conversation_data:
            self.conversation_data = {"messages": []}
            
        self.conversation_data["messages"].append({
            "role": role,  # "human" or "assistant"
            "content": content,
            "timestamp": timestamp
        })
        
        # Mark the column as changed for SQLAlchemy tracking
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, "conversation_data")
        
        # Set title from first human message (first 50 chars)
        if role == "human" and not self.title:
            self.title = content[:50]
    
    def get_last_n_messages(self, n: int = 10):
        """Get last N messages from conversation"""
        if not self.conversation_data or not self.conversation_data.get("messages"):
            return []
        
        messages = self.conversation_data["messages"]
        return messages[-n:] if len(messages) > n else messages
    
    def get_message_count(self) -> int:
        """Get total number of messages in conversation"""
        if not self.conversation_data or not self.conversation_data.get("messages"):
            return 0
        return len(self.conversation_data["messages"])
    
    def is_expired(self) -> bool:
        """Check if chat session has expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at