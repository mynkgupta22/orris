#!/usr/bin/env python3
"""
Check current webhook status and provide solutions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('config/.env')

from app.core.database import SessionLocal
from app.services.webhook_channel_service import WebhookChannelService
from datetime import datetime, timezone

def check_webhook_status():
    """Check the current webhook status and provide actionable insights"""
    
    print("🔍 WEBHOOK STATUS CHECK")
    print("=" * 60)
    
    # Get current webhook from database
    db = SessionLocal()
    try:
        channels = WebhookChannelService.get_active_webhook_channels(db)
        
        if not channels:
            print("❌ No active webhook channels found!")
            print("💡 Solution: Start your application to create webhooks automatically")
            return
        
        print(f"📊 Found {len(channels)} active webhook channel(s):")
        
        for i, channel in enumerate(channels, 1):
            print(f"\n🔗 Webhook {i}:")
            print(f"   Channel ID: {channel.channel_id}")
            print(f"   Folder ID: {channel.folder_id}")
            print(f"   Webhook URL: {channel.webhook_url}")
            print(f"   Status: {channel.status}")
            print(f"   Created: {channel.created_at}")
            
            # Check expiration
            if channel.expiration:
                try:
                    exp_timestamp = int(channel.expiration) / 1000
                    exp_date = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    
                    print(f"   Expires: {exp_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    time_diff = exp_date - now
                    if time_diff.total_seconds() > 0:
                        hours_left = time_diff.total_seconds() / 3600
                        print(f"   Time left: {hours_left:.1f} hours")
                        
                        if hours_left < 6:
                            print("   ⚠️  WARNING: Webhook expires soon!")
                        else:
                            print("   ✅ Webhook is not expired")
                    else:
                        print("   ❌ WEBHOOK HAS EXPIRED!")
                        
                except Exception as e:
                    print(f"   ⚠️  Could not parse expiration: {e}")
            else:
                print("   ⚠️  No expiration time available")
            
            # Check webhook URL
            webhook_url = channel.webhook_url
            print(f"\n🌐 Webhook URL Analysis:")
            
            if "ngrok" in webhook_url:
                print("   ⚠️  Using ngrok URL - this may be temporary!")
                print("   💡 For local testing: Ensure ngrok is running")
                print("   💡 For production: Use your deployment URL")
            elif "localhost" in webhook_url:
                print("   ⚠️  Using localhost URL - only works locally!")
                print("   💡 Google Drive cannot reach localhost URLs")
                print("   💡 Use ngrok for local testing or deployment URL")
            elif "render.com" in webhook_url or "onrender.com" in webhook_url:
                print("   ✅ Using Render deployment URL")
            elif "digitalocean" in webhook_url:
                print("   ✅ Using DigitalOcean deployment URL")
            else:
                print("   ℹ️  Using custom webhook URL")
            
        # Check current environment configuration
        print(f"\n📋 CURRENT ENVIRONMENT CONFIGURATION:")
        
        webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        gdrive_root_id = os.getenv('GDRIVE_ROOT_ID')
        
        print(f"   WEBHOOK_BASE_URL: {webhook_base_url}")
        print(f"   GDRIVE_ROOT_ID: {gdrive_root_id}")
        
        # Compare with database
        if channels and webhook_base_url:
            db_webhook_url = channels[0].webhook_url
            expected_url = f"{webhook_base_url}/webhooks/google-drive"
            
            if db_webhook_url == expected_url:
                print("   ✅ Database webhook URL matches environment config")
            else:
                print("   ⚠️  Database webhook URL differs from environment:")
                print(f"      Database: {db_webhook_url}")
                print(f"      Expected: {expected_url}")
                print("   💡 Restart application to update webhook URL")
        
        # Provide solutions
        print(f"\n💡 SOLUTIONS:")
        
        if any("ngrok" in ch.webhook_url for ch in channels):
            print("   For ngrok users:")
            print("   1. Start ngrok: ngrok http 8001")
            print("   2. Update WEBHOOK_BASE_URL in config/.env with new ngrok URL")
            print("   3. Restart your application")
            
        print("\n   For local development:")
        print("   1. Use ngrok to tunnel your local server")
        print("   2. Update webhook URL in environment")
        print("   3. Test by uploading a file to Google Drive")
        
        print("\n   For production deployment:")
        print("   1. Set WEBHOOK_BASE_URL to your deployment URL")
        print("   2. Deploy and restart your application")
        print("   3. Webhooks will be created automatically")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_webhook_status()
