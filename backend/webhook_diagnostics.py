#!/usr/bin/env python3
"""
Comprehensive webhook troubleshooting script
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from app.core.database import SessionLocal
from app.services.webhook_channel_service import WebhookChannelService
from app.core.config import settings

def diagnose_webhook_issues():
    """Run comprehensive diagnostics for webhook functionality"""
    
    print("🔍 WEBHOOK TROUBLESHOOTING DIAGNOSTICS")
    print("=" * 60)
    
    # 1. Environment Variables Check
    print("\n📋 1. ENVIRONMENT VARIABLES:")
    env_vars = [
        'WEBHOOK_BASE_URL',
        'GDRIVE_ROOT_ID', 
        'GOOGLE_DRIVE_FOLDER_ID',
        'GOOGLE_DRIVE_CREDENTIALS_FILE',
        'DATABASE_URL'
    ]
    
    all_env_vars_set = True
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        status = "✅" if value != "NOT SET" else "❌"
        print(f"   {status} {var}: {value}")
        if value == "NOT SET":
            all_env_vars_set = False
    
    # 2. Check via Pydantic Settings
    print(f"\n📋 2. PYDANTIC SETTINGS (from .env file):")
    try:
        print(f"   Environment file path: {settings.model_config.get('env_file', 'NOT SET')}")
        print(f"   Case sensitive: {settings.model_config.get('case_sensitive', 'NOT SET')}")
        
        # Access settings attributes that might exist
        webhook_url = getattr(settings, 'webhook_base_url', 'NOT FOUND')
        gdrive_root = getattr(settings, 'gdrive_root_id', 'NOT FOUND')
        
        print(f"   WEBHOOK_BASE_URL: {webhook_url}")
        print(f"   GDRIVE_ROOT_ID: {gdrive_root}")
        
    except Exception as e:
        print(f"   ❌ Error accessing settings: {e}")
    
    # 3. File System Check
    print(f"\n📋 3. FILE SYSTEM CHECK:")
    config_path = Path("config")
    env_file = config_path / ".env"
    service_account = config_path / "service-account.json"
    
    print(f"   📁 Config directory exists: {'✅' if config_path.exists() else '❌'}")
    print(f"   📄 .env file exists: {'✅' if env_file.exists() else '❌'}")
    print(f"   🔑 service-account.json exists: {'✅' if service_account.exists() else '❌'}")
    
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                has_webhook_url = 'WEBHOOK_BASE_URL' in content
                has_gdrive_root = 'GDRIVE_ROOT_ID' in content
                print(f"   📝 .env contains WEBHOOK_BASE_URL: {'✅' if has_webhook_url else '❌'}")
                print(f"   📝 .env contains GDRIVE_ROOT_ID: {'✅' if has_gdrive_root else '❌'}")
        except Exception as e:
            print(f"   ❌ Error reading .env file: {e}")
    
    # 4. Database Check
    print(f"\n📋 4. DATABASE WEBHOOK CHANNELS:")
    try:
        db = SessionLocal()
        try:
            channels = WebhookChannelService.get_active_webhook_channels(db)
            print(f"   📊 Active channels: {len(channels)}")
            
            if channels:
                for i, channel in enumerate(channels, 1):
                    print(f"   Channel {i}:")
                    print(f"      ID: {channel.channel_id}")
                    print(f"      Folder: {channel.folder_id}")
                    print(f"      URL: {channel.webhook_url}")
                    print(f"      Status: {channel.status}")
                    print(f"      Created: {channel.created_at}")
                    print(f"      Expiration: {channel.expiration}")
            else:
                print("   ❌ No active webhook channels found!")
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    # 5. Google Drive API Check
    print(f"\n📋 5. GOOGLE DRIVE API ACCESS:")
    try:
        from app.rag.integrations.drive import get_drive_service
        service = get_drive_service()
        if service:
            print("   ✅ Google Drive service initialized successfully")
            
            # Try to access the root folder
            gdrive_folder_id = os.getenv('GDRIVE_ROOT_ID') or os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if gdrive_folder_id:
                try:
                    folder_info = service.files().get(fileId=gdrive_folder_id).execute()
                    print(f"   ✅ Can access folder: {folder_info.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"   ❌ Cannot access folder {gdrive_folder_id}: {e}")
            else:
                print("   ⚠️  No folder ID to test")
        else:
            print("   ❌ Failed to initialize Google Drive service")
            
    except Exception as e:
        print(f"   ❌ Google Drive API error: {e}")
    
    # 6. Summary and Recommendations
    print(f"\n📋 6. SUMMARY & RECOMMENDATIONS:")
    
    issues_found = []
    
    if not all_env_vars_set:
        issues_found.append("Missing required environment variables")
    
    if not service_account.exists():
        issues_found.append("Missing Google service account file")
    
    if issues_found:
        print("   ❌ ISSUES FOUND:")
        for issue in issues_found:
            print(f"      • {issue}")
            
        print("\n   🔧 FIXES NEEDED:")
        if not all_env_vars_set:
            print("      1. Add missing environment variables to config/.env")
            print("      2. Restart the application to load new variables")
        
        if not service_account.exists():
            print("      3. Add Google service account JSON file to config/service-account.json")
            print("      4. Ensure the service account has Google Drive API access")
        
    else:
        print("   ✅ All basic requirements appear to be met!")
        print("   🔄 Try restarting the application to reinitialize webhooks")

if __name__ == "__main__":
    diagnose_webhook_issues()
