#!/usr/bin/env python3
"""
Production Environment Checker
Verifies that all required environment variables are properly set for production deployment
"""

import os
import json
import sys

def check_environment():
    """Check all required environment variables for production"""
    
    print("🔍 PRODUCTION ENVIRONMENT CHECK")
    print("=" * 50)
    
    # Required environment variables
    required_vars = {
        'WEBHOOK_BASE_URL': 'Your production webhook URL (e.g., https://yourapp.onrender.com)',
        'GDRIVE_ROOT_ID': 'Google Drive folder ID to monitor',
        'DATABASE_URL': 'PostgreSQL connection string',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON': 'Service account JSON as string'
    }
    
    # Optional but recommended
    optional_vars = {
        'GOOGLE_WEBHOOK_TOKEN': 'Token for webhook verification',
        'GOOGLE_DRIVE_SCOPES': 'Custom Drive API scopes (optional)',
        'QDRANT_URL': 'Qdrant vector database URL',
        'QDRANT_API_KEY': 'Qdrant API key if required'
    }
    
    print("✅ REQUIRED VARIABLES:")
    all_required_set = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_APPLICATION_CREDENTIALS_JSON':
                # Validate JSON format
                try:
                    json.loads(value)
                    print(f"   {var}: ✅ SET (valid JSON, {len(value)} chars)")
                except json.JSONDecodeError:
                    print(f"   {var}: ❌ SET BUT INVALID JSON")
                    all_required_set = False
            elif var == 'DATABASE_URL':
                # Hide sensitive parts
                if 'postgresql://' in value:
                    print(f"   {var}: ✅ SET (PostgreSQL)")
                else:
                    print(f"   {var}: ⚠️  SET (not PostgreSQL format)")
            else:
                # Truncate long values
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"   {var}: ✅ SET ({display_value})")
        else:
            print(f"   {var}: ❌ NOT SET - {description}")
            all_required_set = False
    
    print("\n📋 OPTIONAL VARIABLES:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            display_value = value[:30] + "..." if len(value) > 30 else value
            print(f"   {var}: ✅ SET ({display_value})")
        else:
            print(f"   {var}: ⚪ NOT SET - {description}")
    
    print("\n" + "=" * 50)
    
    if all_required_set:
        print("🎉 ALL REQUIRED VARIABLES ARE SET!")
        print("✅ Your production environment is properly configured.")
        return True
    else:
        print("❌ MISSING REQUIRED VARIABLES!")
        print("🔧 Please set the missing environment variables before deployment.")
        return False

def test_google_credentials():
    """Test if Google Drive credentials work"""
    print("\n🔧 TESTING GOOGLE DRIVE CREDENTIALS:")
    print("-" * 40)
    
    try:
        # Import here to avoid import errors if modules not available
        import sys
        sys.path.append('/opt/render/project/src/backend')  # Production path
        sys.path.append('/Users/mayank/Desktop/orris/backend')  # Local path
        
        from app.rag.integrations.drive import get_drive_service
        
        service = get_drive_service()
        print("✅ Google Drive service created successfully")
        
        # Test basic API call
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')
        print(f"✅ Connected as: {user_email}")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Drive test failed: {e}")
        return False

if __name__ == "__main__":
    env_ok = check_environment()
    
    if env_ok:
        # Only test credentials if environment is properly set
        test_google_credentials()
    
    print(f"\n{'='*50}")
    if env_ok:
        print("🚀 READY FOR DEPLOYMENT!")
    else:
        print("⚠️  ENVIRONMENT NEEDS FIXING")
        sys.exit(1)
