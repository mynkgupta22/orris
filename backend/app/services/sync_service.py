import os
import logging
from typing import Optional
from datetime import datetime, UTC
from pathlib import Path
import asyncio
from googleapiclient.errors import HttpError

from app.rag.drive import get_drive_service
from app.rag.sync_tracker import track_document_sync, mark_document_synced, mark_document_failed
from app.rag.index_qdrant import delete_document_chunks, upsert_document_chunks
from app.rag.loaders import load_file_to_elements
from app.rag.chunking import chunk_elements
from app.rag.drive import resolve_type_from_mime, classify_from_path, download_file

logger = logging.getLogger(__name__)


async def _get_file_metadata_with_retry(service, file_id: str, max_retries: int = 6):
    """
    Get file metadata from Google Drive with retry logic for 404 errors.
    
    Args:
        service: Google Drive service instance
        file_id: Google Drive file ID
        max_retries: Maximum number of retry attempts
        
    Returns:
        File metadata dict or None if file doesn't exist after retries
        
    Raises:
        HttpError: For non-404 errors
    """
    for attempt in range(max_retries + 1):
        try:
            file_metadata = service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,modifiedTime,parents,webViewLink,trashed'
            ).execute()
            return file_metadata
            
        except HttpError as e:
            if e.resp.status == 404:
                if attempt < max_retries:
                    # Wait with longer exponential backoff for Google Drive processing delays
                    # Start with 3s, then 6s, 12s, 24s, 48s, 96s
                    wait_time = 3 * (2 ** attempt)
                    logger.info(f"File {file_id} not found (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"File {file_id} not found after {max_retries + 1} attempts. This might be:")
                    logger.warning(f"1. A file that was deleted/moved before we could process it")
                    logger.warning(f"2. A webhook notification for a folder change rather than direct file")
                    logger.warning(f"3. A permission issue with accessing the file")
                    return None
            else:
                # For non-404 errors, don't retry
                logger.error(f"Google Drive API error for file {file_id}: Status {e.resp.status}, Response: {e.content}")
                raise
        except Exception as e:
            # For other exceptions, don't retry
            logger.error(f"Unexpected error getting file metadata for {file_id}: {e}")
            raise
    
    return None


async def process_drive_change_notification(
    channel_id: Optional[str],
    resource_state: str,
    resource_id: Optional[str],
    message_number: Optional[str]
):
    """
    Process Google Drive change notifications in background.
    
    Args:
        channel_id: Google's channel ID for the notification
        resource_state: Type of change (update, add, remove, trash)
        resource_id: Google Drive resource ID
        message_number: Sequence number for this notification
    """
    logger.info(f"Processing Drive change: {resource_state} for resource {resource_id}")
    
    try:
        if resource_state in ["remove", "trash"]:
            await _handle_document_deletion(resource_id)
        elif resource_state in ["update", "add"]:
            await _handle_document_upsert(resource_id)
        else:
            logger.warning(f"Unknown resource state: {resource_state}")
            
    except Exception as e:
        logger.error(f"Error processing drive change notification: {e}")
        if resource_id:
            mark_document_failed(resource_id, f"Webhook processing failed: {str(e)}")


async def _handle_document_deletion(file_id: Optional[str]):
    """Handle document deletion from Google Drive"""
    if not file_id:
        logger.warning("No file ID provided for deletion")
        return
    
    try:
        logger.info(f"Deleting document chunks for file: {file_id}")
        
        # Delete chunks from vector database
        deleted_count = delete_document_chunks(file_id)
        logger.info(f"Deleted {deleted_count} chunks for document {file_id}")
        
        # Update sync tracking (mark as deleted)
        from app.models.document_sync import DocumentSync
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            sync_record = db.query(DocumentSync).filter(
                DocumentSync.source_doc_id == file_id
            ).first()
            
            if sync_record:
                sync_record.mark_deleted()
                db.commit()
                logger.info(f"Marked document {file_id} as deleted in sync tracking")
            else:
                logger.warning(f"No sync record found for deleted document {file_id}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error handling document deletion for {file_id}: {e}")
        raise


async def _handle_document_upsert(file_id: Optional[str]):
    """Handle document creation or update from Google Drive"""
    if not file_id:
        logger.warning("No file ID provided for upsert")
        return
    
    try:
        logger.info(f"Processing document upsert for resource: {file_id}")
        
        # Add delay to handle race conditions with file uploads and Google Drive processing
        await asyncio.sleep(5)
        
        # Get resource details from Google Drive with retry logic
        service = get_drive_service()
        
        file_metadata = await _get_file_metadata_with_retry(service, file_id)
        
        if file_metadata is None:
            # Resource doesn't exist after retries
            logger.info(f"Resource {file_id} not accessible - might be a webhook for folder changes or deleted file")
            logger.info(f"Attempting to scan folder {file_id} for recent changes instead")
            
            # Try to scan it as a folder for recent changes
            try:
                await _scan_folder_for_changes(service, file_id)
                logger.info(f"Successfully scanned folder {file_id} for recent changes")
            except Exception as folder_e:
                logger.warning(f"Could not scan {file_id} as folder either: {folder_e}")
            return
        
        # If this is a folder, scan for recently modified files
        if file_metadata.get('mimeType') == 'application/vnd.google-apps.folder':
            logger.info(f"Received folder notification for {file_metadata.get('name')}, scanning for recent changes")
            await _scan_folder_for_changes(service, file_id)
            return
        
        # Skip if file is trashed
        if file_metadata.get('trashed', False):
            await _handle_document_deletion(file_id)
            return
        
        # Check if document needs sync
        modified_time = datetime.fromisoformat(
            file_metadata['modifiedTime'].replace('Z', '+00:00')
        )
        
        # Always process webhook notifications (they indicate changes)
        track_document_sync(file_id, file_metadata['name'], modified_time)
        
        # Process the document
        await _process_single_document(service, file_metadata)
        
    except Exception as e:
        logger.error(f"Error handling document upsert for {file_id}: {e}")
        if file_id:
            mark_document_failed(file_id, f"Upsert processing failed: {str(e)}")
        raise


async def _process_single_document(service, file_metadata):
    """Process a single document from Google Drive"""
    file_id = file_metadata['id']
    file_name = file_metadata['name']
    mime_type = file_metadata['mimeType']
    
    try:
        # Check if file type is supported
        dtype = resolve_type_from_mime(file_name, mime_type)
        if dtype is None:
            logger.info(f"Skipping unsupported file type: {file_name} ({mime_type})")
            return
        
        # Delete existing chunks first (for updates)
        deleted_count = delete_document_chunks(file_id)
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} existing chunks for {file_name}")
        
        # Download file to temporary location
        tmp_dir = Path(os.getenv("INGEST_TMP_DIR", ".ingest_tmp"))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = tmp_dir / f"webhook_{file_id}_{file_name}"
        
        try:
            download_file(service, file_id, dest_path)
            logger.info(f"Downloaded {file_name} to {dest_path}")
        except Exception as e:
            logger.error(f"Failed to download {file_name}: {e}")
            mark_document_failed(file_id, f"Download failed: {str(e)}")
            return
        
        # Determine document classification (PI/Non-PI) from parents
        parents = file_metadata.get('parents', [])
        # For webhook processing, we need to traverse up to determine the classification
        # This is simplified - you may need to implement folder path resolution
        is_pi, uid, roles = False, None, ["non_pi"]  # Default classification
        
        # Build metadata
        base_meta = {
            "source_doc_id": file_id,
            "source_doc_name": file_name,
            "source_doc_type": dtype,
            "source_doc_url": file_metadata.get('webViewLink'),
            "doc_mime_type": mime_type,
            "owner_uid": uid,
            "uid": uid,
            "roles_allowed": roles,
            "is_pi": is_pi,
            "folder_path": "",  # Would need to resolve from parents
            "source_last_modified_at": datetime.fromisoformat(
                file_metadata['modifiedTime'].replace('Z', '+00:00')
            ),
            "ingested_at": datetime.now(UTC),
            "language": "en",
        }
        
        # Process document
        try:
            elements = load_file_to_elements(str(dest_path), base_meta)
            chunks = chunk_elements(elements)
            
            if chunks:
                written = upsert_document_chunks(chunks)
                logger.info(f"Processed {file_name}: {len(elements)} elements, {len(chunks)} chunks, {written} indexed")
                
                # Mark as successfully synced
                mark_document_synced(file_id)
            else:
                logger.warning(f"No chunks generated for {file_name}")
                mark_document_failed(file_id, "No chunks generated")
                
        except Exception as e:
            logger.error(f"Failed to process {file_name}: {e}")
            mark_document_failed(file_id, f"Processing failed: {str(e)}")
        
        # Clean up temporary file
        try:
            dest_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {dest_path}: {e}")
            
    except Exception as e:
        logger.error(f"Error in document processing for {file_id}: {e}")
        mark_document_failed(file_id, f"Document processing error: {str(e)}")
        raise


async def _scan_folder_for_changes(service, folder_id: str):
    """Scan folder and subfolders for recently modified files"""
    try:
        from datetime import datetime, UTC, timedelta
        
        # Look for files modified in the last 10 minutes (increased window for webhook delays)
        cutoff_time = datetime.now(UTC) - timedelta(minutes=10)
        cutoff_str = cutoff_time.isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Scanning folder {folder_id} for files modified after {cutoff_str}")
        
        # First, verify this is actually a folder by trying to get its metadata
        try:
            folder_metadata = service.files().get(
                fileId=folder_id,
                fields='id,name,mimeType'
            ).execute()
            logger.info(f"Confirmed folder: {folder_metadata.get('name')} (mime: {folder_metadata.get('mimeType')})")
        except Exception as e:
            logger.error(f"Could not access folder {folder_id}: {e}")
            raise
        
        # Query for recently modified files in this folder and subfolders
        query = f"'{folder_id}' in parents and modifiedTime > '{cutoff_str}' and trashed = false"
        
        results = service.files().list(
            q=query,
            fields='files(id,name,mimeType,modifiedTime,parents,webViewLink,trashed)',
            orderBy='modifiedTime desc',
            pageSize=50
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"Found {len(files)} recently modified files in folder")
        
        # Process each file
        for file_metadata in files:
            # Skip folders - we only want actual files
            if file_metadata.get('mimeType') == 'application/vnd.google-apps.folder':
                continue
                
            logger.info(f"Processing recently modified file: {file_metadata.get('name')}")
            
            # Process this file
            file_id = file_metadata['id']
            file_name = file_metadata['name']
            
            # Check if document needs sync
            modified_time = datetime.fromisoformat(
                file_metadata['modifiedTime'].replace('Z', '+00:00')
            )
            
            # Track and process the document
            track_document_sync(file_id, file_name, modified_time)
            await _process_single_document(service, file_metadata)
        
        # Also scan subfolders recursively
        subfolder_query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        subfolder_results = service.files().list(
            q=subfolder_query,
            fields='files(id,name)',
            pageSize=50
        ).execute()
        
        subfolders = subfolder_results.get('files', [])
        logger.info(f"Found {len(subfolders)} subfolders to scan")
        
        for subfolder in subfolders:
            await _scan_folder_for_changes(service, subfolder['id'])
            
    except Exception as e:
        logger.error(f"Error scanning folder for changes: {e}")
        raise


# Function to set up Google Drive push notifications
def setup_drive_webhook(webhook_url: str, folder_id: str) -> dict:
    """
    Set up Google Drive push notifications for a specific folder.
    
    Args:
        webhook_url: Your webhook endpoint URL
        folder_id: Google Drive folder ID to watch
        
    Returns:
        Channel information from Google
    """
    service = get_drive_service()
    
    # Channel configuration with unique ID
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    channel_body = {
        'id': f'orris-sync-{folder_id}-{unique_suffix}',
        'type': 'web_hook',
        'address': webhook_url,
        'payload': True,
        'token': os.getenv("GOOGLE_WEBHOOK_TOKEN", "orris-webhook-token")
    }
    
    try:
        # Watch the folder for changes
        response = service.files().watch(
            fileId=folder_id,
            body=channel_body
        ).execute()
        
        logger.info(f"Set up webhook for folder {folder_id}: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to set up webhook: {e}")
        raise