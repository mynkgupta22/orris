import os
import logging
from typing import Optional
from datetime import datetime, UTC
from pathlib import Path
import asyncio
import certifi
from googleapiclient.errors import HttpError
import logging


# Configure SSL certificates for Google API calls
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

from app.rag.integrations.drive import get_drive_service, resolve_type_from_mime, classify_from_path, download_file
from app.rag.storage.sync_tracker import track_document_sync, mark_document_synced, mark_document_failed, document_needs_resync
from app.rag.storage.index_qdrant import delete_document_chunks, upsert_document_chunks
from app.rag.core.loaders import load_file_to_elements
from app.rag.core.chunking import chunk_elements

logger = logging.getLogger(__name__)



try:
    from app.rag.integrations.vision import summarize_image_with_base64
    vision_available = True
except ImportError:
    summarize_image_with_base64 = None
    vision_available = False
import json

logger = logging.getLogger(__name__)


def _get_folder_id_from_channel(channel_id: Optional[str]) -> Optional[str]:
    """
    Look up the folder ID from channel ID using database
    """
    if not channel_id:
        return None
        
    try:
        from app.services.webhook_channel_service import WebhookChannelService
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            # First try exact match
            channel = WebhookChannelService.get_webhook_channel(db, channel_id)
            if channel and channel.status == 'active':
                return channel.folder_id
            
            # If exact match not found, try to find a channel with similar base ID
            # Extract base channel ID (remove the suffix after last dash)
            if '-' in channel_id:
                base_channel_id = '-'.join(channel_id.split('-')[:-1])
                active_channels = WebhookChannelService.get_active_webhook_channels(db)
                
                for channel in active_channels:
                    if channel.channel_id.startswith(base_channel_id):
                        logger.info(f"Found similar channel ID: {channel.channel_id} for requested {channel_id}")
                        return channel.folder_id
            
            logger.warning(f"No folder found for channel ID: {channel_id}")
            return None
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error looking up folder ID for channel {channel_id}: {e}")
        return None
        
        # Final fallback: if channel ID follows our naming pattern, extract folder ID
        if channel_id and channel_id.startswith('orris-sync-'):
            # Extract folder ID from channel naming pattern: orris-sync-{folder_id}-{suffix}
            parts = channel_id.split('-')
            if len(parts) >= 3:
                potential_folder_id = '-'.join(parts[2:-1])  # Remove 'orris', 'sync', and last suffix
                if potential_folder_id:
                    logger.info(f"Extracted potential folder ID from channel name: {potential_folder_id}")
                    return potential_folder_id
                
        logger.warning(f"No active folder found for channel {channel_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error looking up folder ID for channel {channel_id}: {e}")
        return None


async def _resolve_folder_path(service, parents: list) -> list[str]:
    """
    Resolve folder path from parent IDs to get proper classification
    """
    if not parents:
        return []
        
    try:
        # For webhook processing, we typically only have one parent
        parent_id = parents[0]
        path_segments = []
        
        # Traverse up the folder hierarchy to build the path
        current_id = parent_id
        while current_id:
            try:
                folder_metadata = service.files().get(
                    fileId=current_id,
                    fields='id,name,parents'
                ).execute()
                
                folder_name = folder_metadata.get('name')
                if folder_name:
                    path_segments.insert(0, folder_name)
                    
                # Move to next parent
                folder_parents = folder_metadata.get('parents', [])
                current_id = folder_parents[0] if folder_parents else None
                
            except Exception as e:
                logger.warning(f"Could not resolve folder {current_id}: {e}")
                break
                
        return path_segments
        
    except Exception as e:
        logger.error(f"Error resolving folder path: {e}")
        return []


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
    message_number: Optional[str],
    changed: Optional[str] = None
):
    """
    Process Google Drive change notifications in background.
    
    Args:
        channel_id: Google's channel ID for the notification
        resource_state: Type of change (update, add, remove, trash)
        resource_id: Google Drive resource ID
        message_number: Sequence number for this notification
    """
    logger.info(f"Processing Drive change: {resource_state} for resource {resource_id}, changed={changed}")
    
    try:
        # Handle folder change notifications (when files are added/removed from folders)
        if changed == "children" and resource_state in ["update", "add"]:
            logger.info(f"Detected folder children change for channel {channel_id}")
            # Look up the actual folder ID from channel ID
            folder_id = _get_folder_id_from_channel(channel_id)
            if folder_id:
                logger.info(f"Found folder ID {folder_id} for channel {channel_id}, scanning for changes")
                service = get_drive_service()
                await _scan_folder_for_changes(service, folder_id)
            else:
                logger.warning(f"Could not find folder ID for channel {channel_id}")
        elif resource_state in ["remove", "trash"]:
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
        
        # Check if document actually needs re-syncing based on modification time
        if document_needs_resync(file_id, modified_time):
            logger.info(f"Document {file_metadata['name']} needs syncing - processing")
            track_document_sync(file_id, file_metadata['name'], modified_time)
            await _process_single_document(service, file_metadata)
        else:
            logger.info(f"Document {file_metadata['name']} is already up-to-date, skipping sync")
        
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
        try:
            deleted_count = delete_document_chunks(file_id)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} existing chunks for {file_name}")
        except ConnectionError as e:
            logger.error(f"Failed to connect to vector database for deletion: {e}")
            mark_document_failed(file_id, f"Vector database connection failed: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Failed to delete existing chunks for {file_name}: {e}")
            # Continue processing even if deletion fails
        
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
        # Resolve folder path to determine classification
        folder_path = await _resolve_folder_path(service, parents)
        is_pi, uid, roles = classify_from_path(folder_path)
        
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
            "folder_path": "/".join(folder_path),
            "source_last_modified_at": datetime.fromisoformat(
                file_metadata['modifiedTime'].replace('Z', '+00:00')
            ),
            "ingested_at": datetime.now(UTC),
            "language": "en",
        }
        
        # Process document
        try:
            # Use vision with base64 encoding if available
            if vision_available and summarize_image_with_base64:
                elements = load_file_to_elements(str(dest_path), base_meta, summarize_image_with_base64_fn=summarize_image_with_base64)
            else:
                elements = load_file_to_elements(str(dest_path), base_meta)
            chunks = chunk_elements(elements)
            
            if chunks:
                try:
                    written = upsert_document_chunks(chunks)
                    logger.info(f"Processed {file_name}: {len(elements)} elements, {len(chunks)} chunks, {written} indexed")
                    
                    # Mark as successfully synced
                    mark_document_synced(file_id)
                except ConnectionError as e:
                    logger.error(f"Failed to connect to vector database for upsert: {e}")
                    mark_document_failed(file_id, f"Vector database connection failed: {str(e)}")
                    return
                except Exception as e:
                    logger.error(f"Failed to upsert chunks for {file_name}: {e}")
                    mark_document_failed(file_id, f"Vector database upsert failed: {str(e)}")
                    return
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
        
        # Look for files modified in the last 30 minutes (increased window for webhook delays)
        cutoff_time = datetime.now(UTC) - timedelta(minutes=30)
        cutoff_str = cutoff_time.isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Scanning folder {folder_id} for files created or modified after {cutoff_str}")
        
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
        
        # Query for recently modified OR created files in this folder and subfolders
        # When files are uploaded, they might be "created" rather than "modified"
        query = f"'{folder_id}' in parents and (modifiedTime > '{cutoff_str}' or createdTime > '{cutoff_str}') and trashed = false"
        
        results = service.files().list(
            q=query,
            fields='files(id,name,mimeType,modifiedTime,createdTime,parents,webViewLink,trashed)',
            orderBy='modifiedTime desc',
            pageSize=50
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"Found {len(files)} recently modified files in folder")
        
        # Debug: Also show all files (not just recently modified) to understand what's in the folder
        debug_results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields='files(id,name,mimeType,modifiedTime,createdTime)',
            orderBy='modifiedTime desc',
            pageSize=10
        ).execute()
        debug_files = debug_results.get('files', [])
        logger.info(f"Debug: Total files in folder {folder_id}: {len(debug_files)}")
        for file in debug_files[:3]:  # Show first 3 files
            logger.info(f"Debug: File '{file.get('name')}' created at {file.get('createdTime')}, modified at {file.get('modifiedTime')}")
        
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
            
            # Check if document actually needs re-syncing
            if document_needs_resync(file_id, modified_time):
                logger.info(f"Document {file_name} from folder scan needs syncing - processing")
                track_document_sync(file_id, file_name, modified_time)
                await _process_single_document(service, file_metadata)
            else:
                logger.info(f"Document {file_name} from folder scan is already up-to-date, skipping")
        
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
    logger.info(f"Setting up webhook for folder {folder_id} with URL {webhook_url}")
    
    try:
        service = get_drive_service()
        logger.info("Google Drive service obtained successfully")
        
        # Verify folder exists and is accessible
        try:
            folder_info = service.files().get(fileId=folder_id, fields="id,name,mimeType").execute()
            logger.info(f"Target folder verified: {folder_info.get('name')} ({folder_info.get('id')})")
        except Exception as folder_error:
            logger.error(f"Cannot access folder {folder_id}: {folder_error}")
            raise RuntimeError(f"Folder {folder_id} not accessible: {folder_error}")
        
        # Channel configuration with unique ID
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        channel_id = f'orris-sync-{folder_id}-{unique_suffix}'
        
        channel_body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': webhook_url,
            'payload': True,
            'token': os.getenv("GOOGLE_WEBHOOK_TOKEN", "orris-webhook-token")
        }
        
        logger.info(f"Setting up webhook channel: {channel_id}")
        logger.info(f"Webhook payload: {channel_body}")
        
        # Watch the folder for changes
        response = service.files().watch(
            fileId=folder_id,
            body=channel_body
        ).execute()
        
        logger.info(f"✅ Webhook setup successful! Response: {response}")
        return response
        
    except Exception as e:
        import traceback
        logger.error(f"Failed to set up webhook: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise