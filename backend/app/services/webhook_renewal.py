import logging
import os
from datetime import datetime, timedelta
import asyncio
from app.services.sync_service import setup_drive_webhook
from app.services.webhook_channel_service import WebhookChannelService
from app.core.database import get_db

logger = logging.getLogger(__name__)

async def initialize_webhooks_if_needed():
    """Initialize webhooks if no active webhooks exist and environment variables are set"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # Check if we have any active webhooks
        active_channels = WebhookChannelService.get_active_webhook_channels(db)
        
        webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        folder_id = os.getenv('GDRIVE_ROOT_ID')
        
        if not webhook_base_url or not folder_id:
            logger.warning("WEBHOOK_BASE_URL or GDRIVE_ROOT_ID not set, cannot initialize webhooks")
            return False
        
        # Check if we already have an active webhook for this folder
        existing_channels = WebhookChannelService.get_webhook_channels_for_folder(db, folder_id, "active")
        if existing_channels:
            logger.info(f"Active webhook already exists for folder {folder_id}")
            return True
        
        webhook_url = f"{webhook_base_url}/webhooks/google-drive"
        
        logger.info(f"Initializing webhook for folder {folder_id} with URL {webhook_url}")
        
        # Setup the webhook
        channel_info = setup_drive_webhook(webhook_url, folder_id)
        
        # Create the webhook channel in database
        channel_data = {
            "channel_id": channel_info.get('id'),
            "resource_id": channel_info.get('resourceId'),
            "folder_id": folder_id,
            "webhook_url": webhook_url,
            "description": "Main RAG Folder",
            "expiration": channel_info.get('expiration'),
            "status": "active"
        }
        
        WebhookChannelService.create_webhook_channel(db, channel_data)
        
        logger.info(f"✅ Successfully initialized webhook and saved to database")
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
        
        for channel in expiring_channels:
            logger.info(f"Renewing webhook for folder {channel.folder_id}, channel {channel.channel_id}")
            
            try:
                # Setup new webhook
                new_channel_info = setup_drive_webhook(channel.webhook_url, channel.folder_id)
                
                # Update the existing channel with new information
                update_data = {
                    "channel_id": new_channel_info.get('id'),
                    "resource_id": new_channel_info.get('resourceId'),
                    "expiration": new_channel_info.get('expiration'),
                    "status": "active"
                }
                
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
                
                logger.info(f"Successfully renewed webhook: {channel.channel_id} -> {new_channel_info.get('id')}")
                
            except Exception as e:
                logger.error(f"Failed to renew webhook {channel.channel_id}: {str(e)}")
                
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
