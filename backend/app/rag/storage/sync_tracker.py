from typing import Optional
from datetime import datetime, UTC
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from sqlalchemy.orm import Session
from app.models.document_sync import DocumentSync, SyncStatus
from app.core.database import SessionLocal


def get_sync_db():
    """Get synchronous database session for sync operations"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let caller manage


def track_document_sync(
    source_doc_id: str,
    source_doc_name: str,
    last_modified_at: datetime,
    sync_status: SyncStatus = SyncStatus.PENDING
) -> DocumentSync:
    """Create or update document sync tracking record"""
    db = get_sync_db()
    try:
        # Check if document already exists
        existing = db.query(DocumentSync).filter(
            DocumentSync.source_doc_id == source_doc_id
        ).first()
        
        if existing:
            # Update existing record
            existing.source_doc_name = source_doc_name
            existing.last_modified_at = last_modified_at
            existing.sync_status = sync_status
            existing.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new record
            sync_record = DocumentSync(
                source_doc_id=source_doc_id,
                source_doc_name=source_doc_name,
                last_modified_at=last_modified_at,
                sync_status=sync_status
            )
            db.add(sync_record)
            db.commit()
            db.refresh(sync_record)
            return sync_record
    finally:
        db.close()


def mark_document_synced(source_doc_id: str) -> Optional[DocumentSync]:
    """Mark a document as successfully synced"""
    db = get_sync_db()
    try:
        sync_record = db.query(DocumentSync).filter(
            DocumentSync.source_doc_id == source_doc_id
        ).first()
        
        if sync_record:
            sync_record.mark_synced()
            sync_record.last_synced_at = datetime.now(UTC)
            db.commit()
            db.refresh(sync_record)
            return sync_record
        return None
    finally:
        db.close()


def mark_document_failed(source_doc_id: str, error_message: str) -> Optional[DocumentSync]:
    """Mark a document sync as failed"""
    db = get_sync_db()
    try:
        sync_record = db.query(DocumentSync).filter(
            DocumentSync.source_doc_id == source_doc_id
        ).first()
        
        if sync_record:
            sync_record.mark_failed(error_message)
            db.commit()
            db.refresh(sync_record)
            return sync_record
        return None
    finally:
        db.close()


def get_documents_needing_sync() -> list[DocumentSync]:
    """Get all documents that need to be synced"""
    db = get_sync_db()
    try:
        return db.query(DocumentSync).filter(
            DocumentSync.sync_status.in_([SyncStatus.PENDING, SyncStatus.FAILED])
        ).all()
    finally:
        db.close()


def document_needs_resync(source_doc_id: str, drive_modified_time: datetime) -> bool:
    """Check if a document needs to be re-synced based on modification time"""
    db = get_sync_db()
    try:
        sync_record = db.query(DocumentSync).filter(
            DocumentSync.source_doc_id == source_doc_id
        ).first()
        
        if not sync_record:
            return True  # New document, needs sync
        
        return sync_record.needs_sync(drive_modified_time)
    finally:
        db.close()