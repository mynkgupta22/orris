#!/usr/bin/env python3
"""
Test script for Google Drive credential loading
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_drive_credentials():
    """Test both local and production credential loading methods"""
    
    print("🧪 TESTING GOOGLE DRIVE CREDENTIAL LOADING")
    print("=" * 60)
    
    # Test 1: Current configuration
    print("\n📋 1. CURRENT CONFIGURATION:")
    
    env_vars = [
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'GOOGLE_SERVICE_ACCOUNT_FILE', 
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_DRIVE_CREDENTIALS_FILE'
    ]
    
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        if value != "NOT SET":
            # Don't print full JSON content for security
            if var == 'GOOGLE_SERVICE_ACCOUNT_JSON':
                display_value = f"SET (JSON, {len(value)} chars)"
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")
    
    # Test 2: Try to load drive service
    print(f"\n📋 2. GOOGLE DRIVE SERVICE TEST:")
    
    try:
        from app.rag.integrations.drive import get_drive_service
        service = get_drive_service()
        if service:
            print("   ✅ Google Drive service created successfully!")
            
            # Test basic API call
            try:
                about = service.about().get(fields="user").execute()
                user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                print(f"   ✅ API call successful - Service account: {user_email}")
                
                # Test folder access
                gdrive_root_id = os.getenv('GDRIVE_ROOT_ID')
                if gdrive_root_id:
                    folder_info = service.files().get(fileId=gdrive_root_id).execute()
                    folder_name = folder_info.get('name', 'Unknown')
                    print(f"   ✅ Can access target folder: '{folder_name}' ({gdrive_root_id})")
                else:
                    print("   ⚠️  No GDRIVE_ROOT_ID set to test folder access")
                    
            except Exception as api_error:
                print(f"   ❌ API call failed: {api_error}")
                
        else:
            print("   ❌ Failed to create Google Drive service")
            
    except Exception as e:
        print(f"   ❌ Error creating service: {e}")
        
        # Provide specific guidance based on error
        error_str = str(e).lower()
        if "json" in error_str and "decode" in error_str:
            print("   💡 Tip: Check GOOGLE_SERVICE_ACCOUNT_JSON format")
        elif "no such file" in error_str or "file not found" in error_str:
            print("   💡 Tip: Check file path in GOOGLE_SERVICE_ACCOUNT_FILE")
        elif "credentials not found" in error_str:
            print("   💡 Tip: Set either GOOGLE_SERVICE_ACCOUNT_JSON or place service-account.json file")
    
    # Test 3: Production simulation
    print(f"\n📋 3. PRODUCTION MODE SIMULATION:")
    
    # Check if we have a local service account file to simulate production
    from pathlib import Path
    service_account_path = Path("config/service-account.json")
    
    if service_account_path.exists():
        print("   📄 Local service account file found - simulating production mode...")
        
        try:
            # Read the service account file
            with open(service_account_path, 'r') as f:
                json_content = f.read()
            
            # Temporarily set the environment variable
            original_json_env = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'] = json_content
            
            # Test production mode
            from app.rag.integrations.drive import get_drive_service
            service = get_drive_service()
            
            if service:
                print("   ✅ Production mode (JSON env var) works!")
                about = service.about().get(fields="user").execute()
                user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                print(f"   ✅ Service account in production mode: {user_email}")
            else:
                print("   ❌ Production mode failed")
            
            # Restore original environment
            if original_json_env:
                os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'] = original_json_env
            else:
                os.environ.pop('GOOGLE_SERVICE_ACCOUNT_JSON', None)
                
        except Exception as e:
            print(f"   ❌ Production simulation failed: {e}")
    else:
        print("   ⚠️  No local service account file found - cannot simulate production mode")
        print(f"   💡 Place your service-account.json file at: {service_account_path}")
    
    print(f"\n📋 4. DEPLOYMENT GUIDANCE:")
    print("   Local Development:")
    print("   • Place service-account.json in config/ directory")
    print("   • Or set GOOGLE_SERVICE_ACCOUNT_FILE to file path")
    print()
    print("   Production Deployment:")
    print("   • Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
    print("   • Value should be the entire JSON content as a string")
    print("   • Remove newlines and escape quotes if needed")
    print()
    print("   Example for production:")
    print('   GOOGLE_SERVICE_ACCOUNT_JSON=\'{"type":"service_account","project_id":"...",...}\'')

if __name__ == "__main__":
    test_drive_credentials()
