from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from .user import Base


class WebhookChannel(Base):
    __tablename__ = "webhook_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(255), unique=True, index=True, nullable=False)
    resource_id = Column(String(255), nullable=False)
    folder_id = Column(String(255), nullable=False, index=True)
    webhook_url = Column(Text, nullable=False)
    description = Column(String(500), default="Main RAG Folder")
    expiration = Column(String(50), nullable=True)  # Store as string to match Google's format
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WebhookChannel(channel_id='{self.channel_id}', folder_id='{self.folder_id}', status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "resource_id": self.resource_id,
            "folder_id": self.folder_id,
            "webhook_url": self.webhook_url,
            "description": self.description,
            "expiration": self.expiration,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create model instance from dictionary"""
        return cls(
            channel_id=data.get("channel_id"),
            resource_id=data.get("resource_id"),
            folder_id=data.get("folder_id"),
            webhook_url=data.get("webhook_url"),
            description=data.get("description", "Main RAG Folder"),
            expiration=data.get("expiration"),
            status=data.get("status", "active")
        )