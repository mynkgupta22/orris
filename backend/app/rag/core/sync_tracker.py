"""
Module for tracking document synchronization status and history.
This module provides functions to track and update the sync status of documents.
"""

from datetime import datetime
from typing import Optional

from app.core.database import get_db_session
from app.models.document_sync import DocumentSync
from sqlalchemy.orm import Session


def track_document_sync(document_id: str, folder_id: str, status: str = "pending", error_message: Optional[str] = None) -> DocumentSync:
    """
    Track a document sync operation by creating or updating a sync record.
    
    Args:
        document_id: The Google Drive ID of the document
        folder_id: The Google Drive ID of the parent folder
        status: The sync status (pending, synced, failed)
        error_message: Optional error message if sync failed
    
    Returns:
        The created or updated DocumentSync record
    """
    with get_db_session() as db:
        sync_record = (
            db.query(DocumentSync)
            .filter(DocumentSync.document_id == document_id)
            .first()
        )
        
        if not sync_record:
            sync_record = DocumentSync(
                document_id=document_id,
                folder_id=folder_id,
                status=status,
                error_message=error_message,
                last_synced=datetime.utcnow() if status == "synced" else None
            )
            db.add(sync_record)
        else:
            sync_record.status = status
            sync_record.error_message = error_message
            if status == "synced":
                sync_record.last_synced = datetime.utcnow()
                sync_record.error_message = None
            
        db.commit()
        db.refresh(sync_record)
        
        return sync_record


def mark_document_synced(document_id: str) -> DocumentSync:
    """
    Mark a document as successfully synced.
    
    Args:
        document_id: The Google Drive ID of the document
    
    Returns:
        The updated DocumentSync record
    """
    return track_document_sync(document_id, folder_id="", status="synced")


def mark_document_failed(document_id: str, error_message: str) -> DocumentSync:
    """
    Mark a document sync as failed with an error message.
    
    Args:
        document_id: The Google Drive ID of the document
        error_message: The error message explaining why sync failed
    
    Returns:
        The updated DocumentSync record
    """
    return track_document_sync(document_id, folder_id="", status="failed", error_message=error_message)


def document_needs_resync(db: Session, document_id: str) -> bool:
    """
    Check if a document needs to be resynced based on its sync history.
    
    Args:
        db: SQLAlchemy database session
        document_id: The Google Drive ID of the document
    
    Returns:
        True if document should be resynced, False otherwise
    """
    sync_record = (
        db.query(DocumentSync)
        .filter(DocumentSync.document_id == document_id)
        .first()
    )
    
    if not sync_record:
        return True
        
    if sync_record.status == "failed":
        return True
        
    # Add any other conditions that would require a resync
    # For example: last sync was too long ago
    
    return False
