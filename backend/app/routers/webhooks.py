from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
import json
import hmac
import hashlib
import os
from typing import Optional
import logging

from app.services.sync_service import process_drive_change_notification

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/google-drive")
async def google_drive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None),
    x_goog_changed: Optional[str] = Header(None),
):
    """
    Webhook endpoint for Google Drive push notifications.
    
    Google Drive sends notifications when files change in the watched folder.
    """
    try:
        # ===== DETAILED WEBHOOK LOGGING FOR DEBUGGING =====
        print("=" * 80)
        print("🔥 GOOGLE DRIVE WEBHOOK RECEIVED")
        print("=" * 80)
        
        # Log all headers with clear formatting
        all_headers = dict(request.headers)
        print("📋 ALL HEADERS:")
        for key, value in all_headers.items():
            print(f"   {key}: {value}")
        
        # Log specific Google headers
        print("\n🔍 GOOGLE-SPECIFIC HEADERS:")
        print(f"   Channel ID: {x_goog_channel_id}")
        print(f"   Channel Token: {x_goog_channel_token}")
        print(f"   Resource ID: {x_goog_resource_id}")
        print(f"   Resource State: {x_goog_resource_state}")
        print(f"   Message Number: {x_goog_message_number}")
        print(f"   Changed: {x_goog_changed}")
        
        # Get request body and log it
        body = await request.body()
        print(f"\n📦 REQUEST BODY:")
        print(f"   Raw body: {body}")
        print(f"   Body length: {len(body)} bytes")
        
        # Try to parse body as JSON if it's not empty
        if body:
            try:
                body_json = json.loads(body.decode('utf-8'))
                print(f"   Parsed JSON: {json.dumps(body_json, indent=2)}")
            except:
                print(f"   Body is not JSON, raw content: {body.decode('utf-8', errors='ignore')}")
        else:
            print("   Body is empty")
        
        # Log request method and URL
        print(f"\n🌐 REQUEST INFO:")
        print(f"   Method: {request.method}")
        print(f"   URL: {request.url}")
        print(f"   Client: {request.client}")
        
        print("=" * 80)
        
        # Original logging for backwards compatibility
        logger.info(f"Received Google Drive webhook: channel={x_goog_channel_id}, "
                   f"state={x_goog_resource_state}, resource={x_goog_resource_id}, changed={x_goog_changed}")
        logger.info(f"All webhook headers: {all_headers}")
        
        # Special handling for folder change notifications
        if x_goog_changed == 'children' and x_goog_resource_state in ["update", "add"]:
            logger.info(f"Detected folder change notification - children changed in folder {x_goog_resource_id}")
            # For folder changes, we should scan the folder for recent changes
            # Force the resource state to trigger folder scanning
            x_goog_resource_state = "update"
        
        logger.info(f"Webhook body: {body}")
        
        # Log the exact resource state check
        logger.info(f"Checking resource state: '{x_goog_resource_state}' against ['update', 'add', 'remove', 'trash']")
        
        # Verify webhook authenticity (optional but recommended)
        webhook_secret = os.getenv("GOOGLE_WEBHOOK_SECRET")
        if webhook_secret and not _verify_webhook_signature(body, webhook_secret, request.headers):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Handle different resource states
        if x_goog_resource_state in ["update", "add", "remove", "trash"]:
            # Add the notification to background processing queue
            background_tasks.add_task(
                process_drive_change_notification,
                channel_id=x_goog_channel_id,
                resource_state=x_goog_resource_state,
                resource_id=x_goog_resource_id,
                message_number=x_goog_message_number
            )
            
            logger.info(f"Queued background task for {x_goog_resource_state} notification")
        
        elif x_goog_resource_state == "sync":
            # Initial sync notification - can be ignored or logged
            logger.info("Received sync notification from Google Drive")
        
        else:
            logger.warning(f"Unknown resource state: {x_goog_resource_state}")
        
        # Google expects 200 OK response
        return JSONResponse(content={"status": "received"}, status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing Google Drive webhook: {e}")
        # Still return 200 to avoid Google retrying
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=200)


def _verify_webhook_signature(body: bytes, secret: str, headers: dict) -> bool:
    """
    Verify webhook authenticity using channel token.
    Google Drive includes the channel token in headers for verification.
    """
    # Get the channel token from headers
    channel_token = headers.get("x-goog-channel-token")
    expected_token = os.getenv("GOOGLE_WEBHOOK_TOKEN", "orris-webhook-token")
    
    if not channel_token:
        logger.warning("Missing channel token in webhook headers")
        return False
    
    # Verify the token matches what we set up
    if channel_token != expected_token:
        logger.warning(f"Invalid channel token: expected {expected_token}, got {channel_token}")
        return False
    
    # Additional verification: check if channel ID is known
    channel_id = headers.get("x-goog-channel-id")
    if channel_id and not _is_known_channel(channel_id):
        logger.warning(f"Unknown channel ID: {channel_id}")
        return False
    
    return True


def _is_known_channel(channel_id: str) -> bool:
    """
    Check if the channel ID is one we set up.
    In production, you should store active channel IDs in your database.
    """
    # Check if channel follows our naming pattern
    if channel_id.startswith("orris-sync-"):
        return True
    
    # Check against saved channels file (if exists)
    try:
        from pathlib import Path
        import json
        
        channels_file = Path("webhook_channels.json")
        if channels_file.exists():
            with open(channels_file, 'r') as f:
                channels = json.load(f)
                known_ids = [ch.get('channel_id') for ch in channels if ch.get('status') == 'active']
                return channel_id in known_ids
    except Exception as e:
        logger.warning(f"Could not verify channel ID against saved channels: {e}")
    
    # If we can't verify, allow it but log
    logger.info(f"Could not verify channel ID {channel_id}, allowing request")
    return True


@router.get("/google-drive/status")
async def webhook_status():
    """
    Health check endpoint for the webhook system.
    """
    return {
        "status": "active",
        "webhook_secret_configured": bool(os.getenv("GOOGLE_WEBHOOK_SECRET")),
        "service": "google-drive-webhook"
    }