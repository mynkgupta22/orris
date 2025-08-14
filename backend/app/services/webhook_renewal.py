import logging
import os
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Set
from googleapiclient.errors import HttpError
from app.services.sync_service import setup_drive_webhook
from app.services.webhook_channel_service import WebhookChannelService
from app.core.database import get_db

logger = logging.getLogger(__name__)

class DriveFolderService:
    def __init__(self, drive_service):
        self.drive_service = drive_service
    
    def list_immediate_subfolders(self, parent_folder_id: str) -> List[Dict]:
        """Get only direct child folders (one level deep)"""
        try:
            query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, parents, createdTime, modifiedTime)",
                pageSize=1000  # Max allowed
            ).execute()
            
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} immediate subfolders in {parent_folder_id}")
            return folders
            
        except HttpError as e:
            logger.error(f"Error listing subfolders for {parent_folder_id}: {e}")
            return []
    
    def list_all_subfolders_recursive(self, parent_folder_id: str, max_depth: int = 3, visited: Set[str] = None) -> List[Dict]:
        """Get all subfolders recursively with depth limit to prevent infinite loops"""
        if visited is None:
            visited = set()
        
        if parent_folder_id in visited or max_depth <= 0:
            return []
        
        visited.add(parent_folder_id)
        all_folders = []
        
        try:
            # Get immediate children
            immediate_folders = self.list_immediate_subfolders(parent_folder_id)
            all_folders.extend(immediate_folders)
            
            # Recursively get subfolders of each child
            for folder in immediate_folders:
                subfolders = self.list_all_subfolders_recursive(
                    folder['id'], 
                    max_depth - 1, 
                    visited.copy()  # Pass a copy to avoid shared state issues
                )
                all_folders.extend(subfolders)
            
            logger.info(f"Found total {len(all_folders)} folders under {parent_folder_id}")
            return all_folders
            
        except Exception as e:
            logger.error(f"Error in recursive folder discovery for {parent_folder_id}: {e}")
            return all_folders  # Return what we have so far

def get_folders_for_webhook_monitoring(drive_service, root_folder_id: str, include_subfolders: bool = True, recursive: bool = False) -> List[str]:
    """Get list of folder IDs that should have webhooks
    
    Args:
        drive_service: Google Drive API service instance
        root_folder_id: Root folder ID to monitor
        include_subfolders: Whether to include subfolders
        recursive: If True, get all recursive subfolders (use with caution)
    
    Returns:
        List of folder IDs to monitor
    """
    folder_service = DriveFolderService(drive_service)
    
    folders_to_monitor = [root_folder_id]  # Always include root
    
    if include_subfolders:
        try:
            if recursive:
                # Get all subfolders recursively (limited depth for safety)
                subfolders = folder_service.list_all_subfolders_recursive(root_folder_id, max_depth=3)
                logger.info("Using recursive subfolder discovery (max depth: 3)")
            else:
                # Get only immediate subfolders (recommended)
                subfolders = folder_service.list_immediate_subfolders(root_folder_id)
                logger.info("Using immediate subfolders only")
            
            subfolder_ids = [folder['id'] for folder in subfolders]
            folders_to_monitor.extend(subfolder_ids)
            
            logger.info(f"Will monitor {len(folders_to_monitor)} folders total (root + {len(subfolder_ids)} subfolders)")
            
        except Exception as e:
            logger.error(f"Error getting subfolders, will monitor root only: {e}")
    
    return folders_to_monitor

async def initialize_webhooks_if_needed():
    """Initialize webhooks if no active webhooks exist and environment variables are set"""
    from app.core.database import SessionLocal
    from app.rag.integrations.drive import get_drive_service  # Assume this exists
    
    db = SessionLocal()
    try:
        # Check if we have any active webhooks
        active_channels = WebhookChannelService.get_active_webhook_channels(db)
        
        webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        root_folder_id = os.getenv('GDRIVE_ROOT_ID')
        include_subfolders = os.getenv('WEBHOOK_INCLUDE_SUBFOLDERS', 'true').lower() == 'true'
        recursive_subfolders = os.getenv('WEBHOOK_RECURSIVE_SUBFOLDERS', 'false').lower() == 'true'
        
        if not webhook_base_url or not root_folder_id:
            logger.warning("WEBHOOK_BASE_URL or GDRIVE_ROOT_ID not set, cannot initialize webhooks")
            return False
        
        webhook_url = f"{webhook_base_url}/webhooks/google-drive"
        
        # Get Google Drive service
        try:
            drive_service = get_drive_service()
        except Exception as e:
            logger.error(f"Failed to get Drive service: {e}")
            return False
        
        # Get all folders that need webhooks
        folders_to_monitor = get_folders_for_webhook_monitoring(
            drive_service, 
            root_folder_id, 
            include_subfolders=include_subfolders,
            recursive=recursive_subfolders
        )
        
        created_count = 0
        
        for folder_id in folders_to_monitor:
            # Check if we already have an active webhook for this folder
            existing_channels = WebhookChannelService.get_webhook_channels_for_folder(db, folder_id, "active")
            if existing_channels:
                logger.info(f"Active webhook already exists for folder {folder_id}")
                continue
            
            logger.info(f"Initializing webhook for folder {folder_id} with URL {webhook_url}")
            
            try:
                # Setup the webhook
                channel_info = setup_drive_webhook(webhook_url, folder_id)
                
                # Get folder name for description
                try:
                    folder_info = drive_service.files().get(
                        fileId=folder_id,
                        fields="name"
                    ).execute()
                    folder_name = folder_info.get('name', f'Folder {folder_id}')
                except:
                    folder_name = "Main RAG Folder" if folder_id == root_folder_id else f"Subfolder {folder_id}"
                
                # Create the webhook channel in database
                channel_data = {
                    "channel_id": channel_info.get('id'),
                    "resource_id": channel_info.get('resourceId'),
                    "folder_id": folder_id,
                    "webhook_url": webhook_url,
                    "description": folder_name,
                    "expiration": channel_info.get('expiration'),
                    "status": "active"
                }
                
                WebhookChannelService.create_webhook_channel(db, channel_data)
                created_count += 1
                logger.info(f"✅ Successfully created webhook for folder '{folder_name}' ({folder_id})")
                
            except Exception as e:
                logger.error(f"Failed to create webhook for folder {folder_id}: {e}")
        
        if created_count > 0:
            logger.info(f"✅ Successfully initialized {created_count} webhooks")
            return True
        else:
            logger.info("All required webhooks already exist")
            return True
        
    except Exception as e:
        logger.error(f"Failed to initialize webhooks: {e}")
        return False
    finally:
        db.close()

async def check_and_renew_webhooks():
    """Check all active webhooks and renew those nearing expiration"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # First, try to initialize webhooks if none exist
        active_channels = WebhookChannelService.get_active_webhook_channels(db)
        
        if not active_channels:
            logger.info("No active webhook channels found, attempting to initialize...")
            initialized = await initialize_webhooks_if_needed()
            if not initialized:
                logger.warning("Could not initialize webhooks, skipping renewal check")
                return
            # Refresh the active channels list
            active_channels = WebhookChannelService.get_active_webhook_channels(db)
        
        # Get channels that are expiring soon (next 6 hours)
        expiring_channels = WebhookChannelService.get_expiring_channels(db, hours_before_expiry=6)
        
        if not expiring_channels:
            logger.info("No webhooks need renewal at this time")
            return
        
        renewed_count = 0
        failed_count = 0
        
        for channel in expiring_channels:
            logger.info(f"Renewing webhook for folder '{channel.description}' ({channel.folder_id}), channel {channel.channel_id}")
            
            try:
                # Setup new webhook
                new_channel_info = setup_drive_webhook(channel.webhook_url, channel.folder_id)
                
                # Deactivate the old channel
                WebhookChannelService.deactivate_webhook_channel(db, channel.channel_id)
                
                # Create new channel entry
                new_channel_data = {
                    "channel_id": new_channel_info.get('id'),
                    "resource_id": new_channel_info.get('resourceId'),
                    "folder_id": channel.folder_id,
                    "webhook_url": channel.webhook_url,
                    "description": channel.description,
                    "expiration": new_channel_info.get('expiration'),
                    "status": "active"
                }
                
                WebhookChannelService.create_webhook_channel(db, new_channel_data)
                renewed_count += 1
                
                logger.info(f"Successfully renewed webhook: {channel.channel_id} -> {new_channel_info.get('id')}")
                
            except Exception as e:
                logger.error(f"Failed to renew webhook {channel.channel_id}: {str(e)}")
                failed_count += 1
        
        logger.info(f"Renewal process completed: {renewed_count} webhooks renewed, {failed_count} failed")
                
    except Exception as e:
        logger.error(f"Error in webhook renewal process: {str(e)}")
    finally:
        db.close()

async def run_webhook_renewal_service():
    """Run the webhook renewal service continuously"""
    logger.info("Starting webhook renewal service...")
    
    # Try to initialize webhooks on first run
    await initialize_webhooks_if_needed()
    
    while True:
        try:
            await check_and_renew_webhooks()
        except Exception as e:
            logger.error(f"Error in webhook renewal service: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)

async def ensure_webhook_initialized():
    """Public function to ensure webhook is initialized (can be called from startup)"""
    return await initialize_webhooks_if_needed()

async def refresh_webhook_folders():
    """Discover new subfolders and create webhooks for them if needed"""
    from app.core.database import SessionLocal
    from app.rag.integrations.drive import get_drive_service
    
    db = SessionLocal()
    try:
        root_folder_id = os.getenv('GDRIVE_ROOT_ID')
        webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        include_subfolders = os.getenv('WEBHOOK_INCLUDE_SUBFOLDERS', 'true').lower() == 'true'
        recursive_subfolders = os.getenv('WEBHOOK_RECURSIVE_SUBFOLDERS', 'false').lower() == 'true'
        
        if not root_folder_id or not webhook_base_url or not include_subfolders:
            logger.info("Folder refresh skipped - not configured for subfolders")
            return 0
        
        drive_service = get_drive_service()
        webhook_url = f"{webhook_base_url}/webhooks/google-drive"
        
        # Get current folder structure
        current_folders = get_folders_for_webhook_monitoring(
            drive_service, 
            root_folder_id, 
            include_subfolders=True,
            recursive=recursive_subfolders
        )
        
        # Get existing webhook channels
        existing_channels = WebhookChannelService.get_active_webhook_channels(db)
        existing_folder_ids = {channel.folder_id for channel in existing_channels}
        
        # Find new folders that need webhooks
        new_folders = [folder_id for folder_id in current_folders if folder_id not in existing_folder_ids]
        
        if not new_folders:
            logger.info("No new folders found for webhook creation")
            return 0
        
        created_count = 0
        
        for folder_id in new_folders:
            try:
                # Get folder name
                folder_info = drive_service.files().get(
                    fileId=folder_id,
                    fields="name"
                ).execute()
                folder_name = folder_info.get('name', f'Folder {folder_id}')
                
                # Setup the webhook
                channel_info = setup_drive_webhook(webhook_url, folder_id)
                
                # Create the webhook channel in database
                channel_data = {
                    "channel_id": channel_info.get('id'),
                    "resource_id": channel_info.get('resourceId'),
                    "folder_id": folder_id,
                    "webhook_url": webhook_url,
                    "description": folder_name,
                    "expiration": channel_info.get('expiration'),
                    "status": "active"
                }
                
                WebhookChannelService.create_webhook_channel(db, channel_data)
                created_count += 1
                logger.info(f"✅ Created webhook for new folder '{folder_name}' ({folder_id})")
                
            except Exception as e:
                logger.error(f"Failed to create webhook for new folder {folder_id}: {e}")
        
        logger.info(f"Folder refresh completed: {created_count} new webhooks created")
        return created_count
        
    except Exception as e:
        logger.error(f"Error during folder refresh: {e}")
        return 0
    finally:
        db.close()

def migrate_json_to_database():
    """One-time migration function to move data from JSON file to database"""
    try:
        from app.core.paths import WEBHOOK_CHANNELS_PATH
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        try:
            migrated_count = WebhookChannelService.migrate_from_json_file(db, str(WEBHOOK_CHANNELS_PATH))
            logger.info(f"Migration completed: {migrated_count} channels migrated")
            return migrated_count
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return 0