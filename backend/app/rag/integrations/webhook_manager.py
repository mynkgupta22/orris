#!/usr/bin/env python3
"""
Google Drive Webhook Management Script

This script helps you set up, manage, and monitor Google Drive push notifications
for automatic document synchronization.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.rag.integrations.drive import get_drive_service
from app.services.sync_service import setup_drive_webhook


def list_active_channels():
    """List all active webhook channels"""
    print("📋 Active Google Drive Webhook Channels\n")
    
    # Note: Google Drive API doesn't provide a direct way to list channels
    # You need to store channel info in your database or config
    print("⚠️  Google Drive API doesn't provide channel listing.")
    print("   Store channel information in your database for tracking.")
    print("   Active channels expire automatically after ~24-48 hours.\n")


def setup_webhook_for_folder(webhook_url: str, folder_id: str, description: str = ""):
    """Set up a webhook for a specific Google Drive folder"""
    print(f"🔗 Setting up webhook for folder: {folder_id}")
    print(f"   Webhook URL: {webhook_url}")
    print(f"   Description: {description}")
    
    try:
        channel_info = setup_drive_webhook(webhook_url, folder_id)
        
        print("✅ Webhook setup successful!")
        print(f"   Channel ID: {channel_info.get('id')}")
        print(f"   Resource ID: {channel_info.get('resourceId')}")
        print(f"   Expiration: {channel_info.get('expiration')}")
        
        # Save channel info for future reference
        save_channel_info(channel_info, folder_id, webhook_url, description)
        
        return channel_info
        
    except Exception as e:
        print(f"❌ Failed to set up webhook: {e}")
        return None


def save_channel_info(channel_info: dict, folder_id: str, webhook_url: str, description: str):
    """Save channel information to a local file"""
    channels_file = Path("webhook_channels.json")
    
    # Load existing channels
    channels = []
    if channels_file.exists():
        try:
            with open(channels_file, 'r') as f:
                channels = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing channels: {e}")
    
    # Add new channel
    channel_record = {
        "channel_id": channel_info.get('id'),
        "resource_id": channel_info.get('resourceId'),
        "folder_id": folder_id,
        "webhook_url": webhook_url,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "expiration": channel_info.get('expiration'),
        "status": "active"
    }
    
    channels.append(channel_record)
    
    # Save updated channels
    try:
        with open(channels_file, 'w') as f:
            json.dump(channels, f, indent=2)
        print(f"💾 Channel info saved to {channels_file}")
    except Exception as e:
        print(f"Warning: Could not save channel info: {e}")


def stop_webhook_channel(channel_id: str):
    """Stop a specific webhook channel"""
    print(f"🛑 Stopping webhook channel: {channel_id}")
    
    try:
        service = get_drive_service()
        
        # Stop the channel
        service.channels().stop(body={'id': channel_id}).execute()
        
        print("✅ Channel stopped successfully!")
        
        # Update local records
        update_channel_status(channel_id, "stopped")
        
    except Exception as e:
        print(f"❌ Failed to stop channel: {e}")


def update_channel_status(channel_id: str, status: str):
    """Update channel status in local records"""
    channels_file = Path("webhook_channels.json")
    
    if not channels_file.exists():
        return
    
    try:
        with open(channels_file, 'r') as f:
            channels = json.load(f)
        
        # Update channel status
        for channel in channels:
            if channel.get('channel_id') == channel_id:
                channel['status'] = status
                channel['updated_at'] = datetime.now().isoformat()
                break
        
        # Save updated channels
        with open(channels_file, 'w') as f:
            json.dump(channels, f, indent=2)
            
    except Exception as e:
        print(f"Warning: Could not update channel status: {e}")


def show_saved_channels():
    """Show saved channel information"""
    channels_file = Path("webhook_channels.json")
    
    if not channels_file.exists():
        print("📋 No saved webhook channels found.")
        return
    
    try:
        with open(channels_file, 'r') as f:
            channels = json.load(f)
        
        print("📋 Saved Webhook Channels\n")
        
        for i, channel in enumerate(channels, 1):
            status = channel.get('status', 'unknown')
            status_icon = "✅" if status == "active" else "🛑" if status == "stopped" else "❓"
            
            print(f"{i}. {status_icon} {channel.get('description', 'Unnamed Channel')}")
            print(f"   Channel ID: {channel.get('channel_id')}")
            print(f"   Folder ID: {channel.get('folder_id')}")
            print(f"   Status: {status}")
            print(f"   Created: {channel.get('created_at')}")
            if channel.get('expiration'):
                exp_ts = int(channel.get('expiration')) / 1000
                exp_date = datetime.fromtimestamp(exp_ts)
                print(f"   Expires: {exp_date}")
            print()
            
    except Exception as e:
        print(f"❌ Error reading saved channels: {e}")


def main():
    """Main CLI interface"""
    print("🔄 Google Drive Webhook Manager\n")
    
    # Check configuration
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"):
        print("❌ Error: Google service account credentials not configured")
        print("   Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_FILE")
        return
    
    # Get environment variables
    gdrive_root_id = os.getenv("GDRIVE_ROOT_ID")
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-domain.com")
    
    if not gdrive_root_id:
        print("⚠️  GDRIVE_ROOT_ID not set. You'll need to specify folder IDs manually.")
    
    print("Available commands:")
    print("1. Setup webhook for main folder")
    print("2. Setup webhook for custom folder")
    print("3. Setup webhooks for all subfolders")
    print("4. Show saved channels")
    print("5. Stop a channel")
    print("6. Test webhook setup")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter command (0-6): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                if not gdrive_root_id:
                    print("❌ GDRIVE_ROOT_ID not configured")
                    continue
                webhook_url = f"{webhook_base_url}/webhooks/google-drive"
                setup_webhook_for_folder(webhook_url, gdrive_root_id, "Main RAG Folder")
            elif choice == "2":
                folder_id = input("Enter Google Drive folder ID: ").strip()
                description = input("Enter description (optional): ").strip()
                webhook_url = f"{webhook_base_url}/webhooks/google-drive"
                setup_webhook_for_folder(webhook_url, folder_id, description or "Custom Folder")
            elif choice == "3":
                if not gdrive_root_id:
                    print("❌ GDRIVE_ROOT_ID not configured")
                    continue
                webhook_url = f"{webhook_base_url}/webhooks/google-drive"
                setup_webhooks_for_subfolders(webhook_url, gdrive_root_id)
            elif choice == "4":
                show_saved_channels()
            elif choice == "5":
                channel_id = input("Enter channel ID to stop: ").strip()
                stop_webhook_channel(channel_id)
            elif choice == "6":
                test_webhook_setup()
            else:
                print("Invalid choice. Please enter 0-6.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def setup_webhooks_for_subfolders(webhook_url: str, root_folder_id: str):
    """Set up webhooks for all subfolders in the root folder"""
    print(f"🔗 Setting up webhooks for all subfolders in: {root_folder_id}")
    
    try:
        service = get_drive_service()
        
        # Get all folders in the root directory
        query = f"'{root_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields='files(id,name)',
            pageSize=50
        ).execute()
        
        folders = results.get('files', [])
        print(f"Found {len(folders)} subfolders to set up webhooks for")
        
        success_count = 0
        for folder in folders:
            try:
                folder_id = folder['id']
                folder_name = folder['name']
                print(f"\n📁 Setting up webhook for: {folder_name}")
                
                setup_webhook_for_folder(webhook_url, folder_id, f"Subfolder: {folder_name}")
                success_count += 1
                
                # If this is the PI folder, also set up webhooks for its subfolders
                if folder_name.upper() == 'PI':
                    print(f"   📂 Setting up webhooks for PI subfolders...")
                    setup_webhooks_recursively(service, webhook_url, folder_id, f"{folder_name}/")
                    
            except Exception as e:
                print(f"   ❌ Failed to set up webhook for {folder.get('name', 'unknown')}: {e}")
        
        print(f"\n✅ Successfully set up webhooks for {success_count}/{len(folders)} subfolders")
        
    except Exception as e:
        print(f"❌ Error setting up subfolder webhooks: {e}")


def setup_webhooks_recursively(service, webhook_url: str, parent_folder_id: str, path_prefix: str = ""):
    """Recursively set up webhooks for subfolders"""
    try:
        query = f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields='files(id,name)',
            pageSize=50
        ).execute()
        
        folders = results.get('files', [])
        print(f"     Found {len(folders)} subfolders in {path_prefix}")
        
        for folder in folders:
            try:
                folder_id = folder['id']
                folder_name = folder['name']
                folder_path = f"{path_prefix}{folder_name}"
                
                print(f"     📁 Setting up webhook for: {folder_path}")
                setup_webhook_for_folder(webhook_url, folder_id, f"Subfolder: {folder_path}")
                
            except Exception as e:
                print(f"     ❌ Failed to set up webhook for {folder_path}: {e}")
                
    except Exception as e:
        print(f"     ❌ Error in recursive setup: {e}")


def test_webhook_setup():
    """Test webhook configuration"""
    print("🧪 Testing Webhook Setup\n")
    
    # Check webhook URL accessibility
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL")
    if not webhook_base_url:
        print("❌ WEBHOOK_BASE_URL not configured")
        print("   Set this to your public domain (e.g., https://your-domain.com)")
        return
    
    webhook_url = f"{webhook_base_url}/webhooks/google-drive"
    print(f"Webhook URL: {webhook_url}")
    
    # Check Google credentials
    try:
        service = get_drive_service()
        print("✅ Google Drive API connection successful")
    except Exception as e:
        print(f"❌ Google Drive API connection failed: {e}")
        return
    
    # Check required environment variables
    required_vars = ["GDRIVE_ROOT_ID", "WEBHOOK_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
    else:
        print("✅ All required environment variables configured")
    
    print("\n📝 Next steps:")
    print("1. Ensure your webhook URL is publicly accessible")
    print("2. Configure your firewall to allow Google's IPs")
    print("3. Set up HTTPS with valid SSL certificate")
    print("4. Run setup webhook for your folder")


if __name__ == "__main__":
    main()