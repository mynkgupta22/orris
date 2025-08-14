from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import logging

from app.models.webhook_channel import WebhookChannel
from app.core.database import get_db

logger = logging.getLogger(__name__)


class WebhookChannelService:
    """Service class for managing webhook channels in PostgreSQL database"""

    @staticmethod
    def create_webhook_channel(db: Session, channel_data: Dict[str, Any]) -> WebhookChannel:
        """Create a new webhook channel"""
        try:
            # First, deactivate any existing active channels for the same folder
            WebhookChannelService.deactivate_channels_for_folder(db, channel_data.get("folder_id"))
            
            # Create new channel
            webhook_channel = WebhookChannel.from_dict(channel_data)
            db.add(webhook_channel)
            db.commit()
            db.refresh(webhook_channel)
            
            logger.info(f"Created webhook channel: {webhook_channel.channel_id}")
            return webhook_channel
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating webhook channel: {e}")
            raise

    @staticmethod
    def get_webhook_channel(db: Session, channel_id: str) -> Optional[WebhookChannel]:
        """Get a webhook channel by channel_id"""
        return db.query(WebhookChannel).filter(WebhookChannel.channel_id == channel_id).first()

    @staticmethod
    def get_webhook_channels_for_folder(db: Session, folder_id: str, status: str = "active") -> List[WebhookChannel]:
        """Get webhook channels for a specific folder"""
        query = db.query(WebhookChannel).filter(WebhookChannel.folder_id == folder_id)
        if status:
            query = query.filter(WebhookChannel.status == status)
        return query.all()

    @staticmethod
    def get_active_webhook_channels(db: Session) -> List[WebhookChannel]:
        """Get all active webhook channels"""
        return db.query(WebhookChannel).filter(WebhookChannel.status == "active").all()

    @staticmethod
    def update_webhook_channel(db: Session, channel_id: str, update_data: Dict[str, Any]) -> Optional[WebhookChannel]:
        """Update a webhook channel"""
        try:
            webhook_channel = WebhookChannelService.get_webhook_channel(db, channel_id)
            if not webhook_channel:
                logger.warning(f"Webhook channel not found: {channel_id}")
                return None

            # Update fields
            for key, value in update_data.items():
                if hasattr(webhook_channel, key):
                    setattr(webhook_channel, key, value)
            
            webhook_channel.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(webhook_channel)
            
            logger.info(f"Updated webhook channel: {channel_id}")
            return webhook_channel
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating webhook channel {channel_id}: {e}")
            raise

    @staticmethod
    def deactivate_webhook_channel(db: Session, channel_id: str) -> Optional[WebhookChannel]:
        """Deactivate a webhook channel"""
        return WebhookChannelService.update_webhook_channel(
            db, channel_id, {"status": "inactive"}
        )

    @staticmethod
    def deactivate_channels_for_folder(db: Session, folder_id: str) -> int:
        """Deactivate all active channels for a specific folder"""
        try:
            count = db.query(WebhookChannel).filter(
                and_(
                    WebhookChannel.folder_id == folder_id,
                    WebhookChannel.status == "active"
                )
            ).update({
                "status": "inactive", 
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            logger.info(f"Deactivated {count} webhook channels for folder {folder_id}")
            return count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deactivating channels for folder {folder_id}: {e}")
            raise

    @staticmethod
    def delete_webhook_channel(db: Session, channel_id: str) -> bool:
        """Permanently delete a webhook channel"""
        try:
            webhook_channel = WebhookChannelService.get_webhook_channel(db, channel_id)
            if not webhook_channel:
                return False

            db.delete(webhook_channel)
            db.commit()
            
            logger.info(f"Deleted webhook channel: {channel_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting webhook channel {channel_id}: {e}")
            raise

    @staticmethod
    def get_expiring_channels(db: Session, hours_before_expiry: int = 6) -> List[WebhookChannel]:
        """Get channels that are expiring soon"""
        try:
            current_time_ms = int(datetime.now().timestamp() * 1000)
            expiry_threshold = current_time_ms + (hours_before_expiry * 60 * 60 * 1000)
            
            # Note: Since expiration is stored as string, we need to filter in Python
            # For better performance in production, consider storing expiration as DateTime
            active_channels = WebhookChannelService.get_active_webhook_channels(db)
            expiring_channels = []
            
            for channel in active_channels:
                if channel.expiration:
                    try:
                        expiration_ms = int(channel.expiration)
                        if expiration_ms <= expiry_threshold:
                            expiring_channels.append(channel)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid expiration format for channel {channel.channel_id}: {channel.expiration}")
            
            return expiring_channels
            
        except Exception as e:
            logger.error(f"Error getting expiring channels: {e}")
            return []

    @staticmethod
    def migrate_from_json_file(db: Session, json_file_path: str) -> int:
        """Migrate webhook channels from JSON file to database"""
        import json
        import os
        
        if not os.path.exists(json_file_path):
            logger.info(f"JSON file not found: {json_file_path}")
            return 0
        
        try:
            with open(json_file_path, 'r') as f:
                channels_data = json.load(f)
            
            migrated_count = 0
            for channel_data in channels_data:
                try:
                    # Check if channel already exists
                    existing_channel = WebhookChannelService.get_webhook_channel(
                        db, channel_data.get("channel_id")
                    )
                    
                    if not existing_channel:
                        WebhookChannelService.create_webhook_channel(db, channel_data)
                        migrated_count += 1
                    else:
                        logger.info(f"Channel already exists: {channel_data.get('channel_id')}")
                        
                except Exception as e:
                    logger.error(f"Error migrating channel {channel_data.get('channel_id')}: {e}")
                    continue
            
            logger.info(f"Migrated {migrated_count} webhook channels from JSON to database")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Error migrating from JSON file: {e}")
            return 0


# Convenience functions for easy database access
def get_db_session():
    """Get database session"""
    return next(get_db())

def create_webhook_channel(channel_data: Dict[str, Any]) -> WebhookChannel:
    """Create webhook channel with automatic session management"""
    db = get_db_session()
    try:
        return WebhookChannelService.create_webhook_channel(db, channel_data)
    finally:
        db.close()

def get_active_webhook_channels() -> List[Dict[str, Any]]:
    """Get active webhook channels as dictionaries"""
    db = get_db_session()
    try:
        channels = WebhookChannelService.get_active_webhook_channels(db)
        return [channel.to_dict() for channel in channels]
    finally:
        db.close()

def update_webhook_channel(channel_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update webhook channel with automatic session management"""
    db = get_db_session()
    try:
        channel = WebhookChannelService.update_webhook_channel(db, channel_id, update_data)
        return channel.to_dict() if channel else None
    finally:
        db.close()
