import logging
from pathlib import Path
import json
from datetime import datetime, timedelta
import asyncio
from app.services.sync_service import setup_drive_webhook

logger = logging.getLogger(__name__)

async def check_and_renew_webhooks():
    """Check all active webhooks and renew those nearing expiration"""
    from app.core.paths import WEBHOOK_CHANNELS_PATH
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
                continue
                
            expiration = float(channel.get('expiration', 0))
            
            # If webhook expires in next 6 hours, renew it
            if expiration - current_time <= 6 * 60 * 60 * 1000:  # 6 hours in milliseconds
                logger.info(f"Renewing webhook for folder {channel.get('folder_id')}")
                
                try:
                    # Setup new webhook
                    new_channel_info = setup_drive_webhook(
                        channel.get('webhook_url'),
                        channel.get('folder_id')
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
