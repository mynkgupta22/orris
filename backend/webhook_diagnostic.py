#!/usr/bin/env python3
"""
Webhook Setup Diagnostic Tool
Checks all requirements for Google Drive webhook setup
"""

import os
import json
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_service_account_permissions():
    """Check if service account has required permissions"""
    print("🔐 CHECKING SERVICE ACCOUNT PERMISSIONS")
    print("-" * 50)
    
    try:
        # Add current directory to path for imports
        sys.path.append('/opt/render/project/src/backend')
        sys.path.append('.')
        
        from app.rag.integrations.drive import get_drive_service
        
        service = get_drive_service()
        print("✅ Service account credentials loaded")
        
        # Test basic permissions
        try:
            about = service.about().get(fields="user,storageQuota").execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            print(f"✅ Connected as: {user_email}")
            
            # Test if we can access the target folder
            folder_id = os.getenv('GDRIVE_ROOT_ID')
            if folder_id:
                folder_info = service.files().get(fileId=folder_id, fields="id,name,mimeType,permissions").execute()
                print(f"✅ Can access target folder: {folder_info.get('name')}")
                
                # Check folder permissions
                permissions = folder_info.get('permissions', [])
                print(f"   Folder has {len(permissions)} permission entries")
                
                # Test if we can list files (required for webhooks)
                files = service.files().list(
                    q=f"'{folder_id}' in parents",
                    fields="files(id,name)",
                    pageSize=5
                ).execute()
                
                file_count = len(files.get('files', []))
                print(f"✅ Can list folder contents: {file_count} files found")
                
            else:
                print("⚠️  GDRIVE_ROOT_ID not set, cannot test folder access")
                
        except Exception as perm_error:
            print(f"❌ Permission test failed: {perm_error}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Service account test failed: {e}")
        return False

def check_webhook_requirements():
    """Check webhook-specific requirements"""
    print("\n🌐 CHECKING WEBHOOK REQUIREMENTS")
    print("-" * 50)
    
    webhook_url = os.getenv('WEBHOOK_BASE_URL')
    if not webhook_url:
        print("❌ WEBHOOK_BASE_URL not set")
        return False
    
    print(f"📍 Webhook URL: {webhook_url}")
    
    # Check URL format
    if not webhook_url.startswith('https://'):
        print("❌ Webhook URL must use HTTPS")
        return False
    else:
        print("✅ Using HTTPS")
    
    # Check if URL is publicly accessible
    try:
        import requests
        full_webhook_url = f"{webhook_url}/webhooks/google-drive"
        
        print(f"🔍 Testing webhook endpoint: {full_webhook_url}")
        
        # Test GET request (should return 405 Method Not Allowed)
        response = requests.get(full_webhook_url, timeout=10)
        if response.status_code == 405:
            print("✅ Webhook endpoint is accessible (405 Method Not Allowed expected)")
        elif response.status_code == 200:
            print("✅ Webhook endpoint is accessible")
        else:
            print(f"⚠️  Webhook endpoint returned: {response.status_code}")
        
        # Test POST request with empty body
        try:
            post_response = requests.post(full_webhook_url, json={}, timeout=10)
            print(f"✅ POST test successful: {post_response.status_code}")
        except Exception as post_error:
            print(f"⚠️  POST test failed: {post_error}")
        
        return True
        
    except Exception as url_error:
        print(f"❌ Webhook URL not accessible: {url_error}")
        return False

def test_webhook_setup():
    """Attempt to set up a test webhook"""
    print("\n🧪 TESTING WEBHOOK SETUP")
    print("-" * 50)
    
    try:
        sys.path.append('/opt/render/project/src/backend')
        sys.path.append('.')
        
        from app.services.sync_service import setup_drive_webhook
        
        webhook_url = os.getenv('WEBHOOK_BASE_URL')
        folder_id = os.getenv('GDRIVE_ROOT_ID')
        
        if not webhook_url or not folder_id:
            print("❌ Missing WEBHOOK_BASE_URL or GDRIVE_ROOT_ID")
            return False
        
        full_webhook_url = f"{webhook_url}/webhooks/google-drive"
        
        print(f"🔄 Attempting webhook setup...")
        print(f"   URL: {full_webhook_url}")
        print(f"   Folder: {folder_id}")
        
        result = setup_drive_webhook(full_webhook_url, folder_id)
        
        print("✅ WEBHOOK SETUP SUCCESSFUL!")
        print(f"   Channel ID: {result.get('id')}")
        print(f"   Resource ID: {result.get('resourceId')}")
        print(f"   Expiration: {result.get('expiration')}")
        
        return True
        
    except Exception as setup_error:
        print(f"❌ Webhook setup failed: {setup_error}")
        
        # Provide specific troubleshooting based on error
        error_str = str(setup_error).lower()
        
        if "no such file or directory" in error_str:
            print("\n💡 TROUBLESHOOTING:")
            print("   - This error suggests missing dependencies or modules")
            print("   - Check if all required Python packages are installed")
            print("   - Verify that googleapiclient is properly installed")
            
        elif "permission" in error_str or "forbidden" in error_str:
            print("\n💡 TROUBLESHOOTING:")
            print("   - Service account needs domain-wide delegation")
            print("   - Or folder must be shared with service account email")
            print("   - Check Google Workspace admin console")
            
        elif "invalid" in error_str or "token" in error_str:
            print("\n💡 TROUBLESHOOTING:")
            print("   - Check service account JSON format")
            print("   - Verify service account has correct scopes")
            print("   - Ensure webhook URL is publicly accessible")
            
        return False

def main():
    """Run all webhook diagnostics"""
    print("🔍 GOOGLE DRIVE WEBHOOK DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check environment
    required_vars = ['WEBHOOK_BASE_URL', 'GDRIVE_ROOT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    # Run checks
    checks = [
        check_service_account_permissions,
        check_webhook_requirements,
        test_webhook_setup
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Webhooks should work.")
    else:
        print("❌ SOME CHECKS FAILED. Review errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
