import logging
from pathlib import Path
import json
from datetime import datetime, timedelta
import asyncio
import os
from app.services.sync_service import setup_drive_webhook

logger = logging.getLogger(__name__)

def ensure_webhook_channels_file():
    """Ensure the webhook_channels.json file exists with proper structure"""
    from app.core.paths import WEBHOOK_CHANNELS_PATH
    
    # Create config directory if it doesn't exist
    WEBHOOK_CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not WEBHOOK_CHANNELS_PATH.exists():
        logger.info("Creating webhook_channels.json file as it doesn't exist")
        
        # Get the base URL from environment variable
        base_url = os.environ.get("WEBHOOK_BASE_URL", "https://orris-backend.onrender.com")
        webhook_url = f"{base_url}/webhooks/google-drive"
        
        # Default folder IDs from your local file
        default_folders = [
            "1NmJmAGWP4TMIzw4Algfl5OkiWgYdsfgh",  # Main RAG Folder
            "1NaJHy1DpoN-i4zpPzNfl1yeGWKuOxhfN",  # Subfolder: PI
            "1ybSOgUKJlMkrDU1CxoOS0ER8amBtEg5B",  # Subfolder: PI/4
            "10ECPTmi04z6e7ft9BrHf-z7ddJvmipl2",  # Subfolder: PI/1
            "1dhHERNcFhlBBSRYbhZnLICqx9HhFVV4n",  # Subfolder: NonPI
        ]
        
        # Create initial channels structure
        channels = []
        for folder_id in default_folders:
            channel = {
                "channel_id": f"orris-sync-{folder_id}-initial",
                "resource_id": "",
                "folder_id": folder_id,
                "webhook_url": webhook_url,
                "description": f"Auto-created for folder {folder_id}",
                "created_at": datetime.now().isoformat(),
                "expiration": "0",  # Will be set when webhook is actually created
                "status": "pending",  # Will be set to active when webhook is created
                "updated_at": datetime.now().isoformat()
            }
            channels.append(channel)
        
        # Write the file
        with open(WEBHOOK_CHANNELS_PATH, 'w') as f:
            json.dump(channels, f, indent=2)
        
        logger.info(f"Created webhook_channels.json with {len(channels)} default folders")
        return True
    
    return False

async def check_and_renew_webhooks():
    """Check all active webhooks and renew those nearing expiration"""
    from app.core.paths import WEBHOOK_CHANNELS_PATH
    
    # Ensure the file exists
    ensure_webhook_channels_file()
    
    channels_file = WEBHOOK_CHANNELS_PATH
    
    if not channels_file.exists():
        logger.warning("No webhook channels file found")
        return
    
    try:
        with open(channels_file, 'r') as f:
            channels = json.load(f)
        
        current_time = datetime.now().timestamp() * 1000  # Convert to milliseconds
        
        for channel in channels:
            if channel.get('status') != 'active':
                # Try to create webhook for pending channels
                if channel.get('status') == 'pending':
                    logger.info(f"Creating webhook for pending folder {channel.get('folder_id')}")
                    try:
                        new_channel_info = setup_drive_webhook(
                            folder_id=channel.get('folder_id')
                        )
                        
                        # Update channel information
                        channel['channel_id'] = new_channel_info.get('id')
                        channel['resource_id'] = new_channel_info.get('resourceId')
                        channel['expiration'] = new_channel_info.get('expiration')
                        channel['status'] = 'active'
                        channel['updated_at'] = datetime.now().isoformat()
                        
                        logger.info(f"Successfully created webhook channel {channel.get('channel_id')}")
                        
                    except Exception as e:
                        logger.error(f"Failed to create webhook: {str(e)}")
                        continue
                else:
                    continue
                
            expiration = float(channel.get('expiration', 0))
            
            # If webhook expires in next 6 hours, renew it
            if expiration - current_time <= 6 * 60 * 60 * 1000:  # 6 hours in milliseconds
                logger.info(f"Renewing webhook for folder {channel.get('folder_id')}")
                
                try:
                    # Setup new webhook
                    new_channel_info = setup_drive_webhook(
                        folder_id=channel.get('folder_id')
                    )
                    
                    # Update channel information
                    channel['channel_id'] = new_channel_info.get('id')
                    channel['resource_id'] = new_channel_info.get('resourceId')
                    channel['expiration'] = new_channel_info.get('expiration')
                    channel['updated_at'] = datetime.now().isoformat()
                    
                    logger.info(f"Successfully renewed webhook channel {channel.get('channel_id')}")
                    
                except Exception as e:
                    logger.error(f"Failed to renew webhook: {str(e)}")
        
        # Save updated channels back to file
        with open(channels_file, 'w') as f:
            json.dump(channels, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in webhook renewal process: {str(e)}")

async def run_webhook_renewal_service():
    """Run the webhook renewal service continuously"""
    while True:
        await check_and_renew_webhooks()
        # Check every hour
        await asyncio.sleep(3600)
