from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.core.database import Base


class SyncStatus(str, enum.Enum):
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentSync(Base):
    __tablename__ = "document_sync"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    source_doc_id = Column(String(255), unique=True, index=True, nullable=False)  # Google Drive file ID
    source_doc_name = Column(String(500), nullable=False)
    last_modified_at = Column(DateTime(timezone=True), nullable=False)  # From Google Drive
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # When we last synced
    sync_status = Column(Enum(SyncStatus), default=SyncStatus.PENDING, nullable=False)
    error_message = Column(String(1000), nullable=True)  # Store sync error details
    retry_count = Column(String(10), default="0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def mark_synced(self):
        """Mark document as successfully synced"""
        self.sync_status = SyncStatus.SYNCED
        self.last_synced_at = func.now()
        self.error_message = None
        self.retry_count = "0"

    def mark_failed(self, error_message: str):
        """Mark document sync as failed with error message"""
        self.sync_status = SyncStatus.FAILED
        self.error_message = error_message
        current_retry = int(self.retry_count or "0")
        self.retry_count = str(current_retry + 1)

    def mark_deleted(self):
        """Mark document as deleted from source"""
        self.sync_status = SyncStatus.DELETED

    def needs_sync(self, drive_modified_time) -> bool:
        """Check if document needs to be re-synced based on modification time"""
        if self.sync_status == SyncStatus.DELETED:
            return False
        if self.last_synced_at is None or self.sync_status != SyncStatus.SYNCED:
            return True
        # Compare drive modification time with our stored modification time
        # If Google Drive's version is newer than what we have, we need to sync
        return drive_modified_time > self.last_modified_at