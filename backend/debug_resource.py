#!/usr/bin/env python3
"""
Debug script to identify what the resource ID dJJu_fLSv-M2qZoUACGzL4d4NCE is
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from app.rag.drive import get_drive_service
from googleapiclient.errors import HttpError

def debug_resource():
    bad_resource_id = "dJJu_fLSv-M2qZoUACGzL4d4NCE"
    root_folder_id = os.getenv("GDRIVE_ROOT_ID", "1NmJmAGWP4TMIzw4Algfl5OkiWgYdsfgh")
    
    print(f"Investigating bad resource ID: {bad_resource_id}")
    print(f"Your configured root folder ID: {root_folder_id}")
    print("=" * 60)
    
    try:
        service = get_drive_service()
        print("✓ Google Drive service initialized")
        
        # First check the root folder
        print(f"\n📁 Checking your root folder ({root_folder_id}):")
        try:
            root_metadata = service.files().get(
                fileId=root_folder_id,
                fields='id,name,mimeType,modifiedTime,parents,webViewLink,trashed,size,owners'
            ).execute()
            
            print(f"  ✓ Root folder exists: {root_metadata.get('name')}")
            print(f"  ✓ Type: {root_metadata.get('mimeType')}")
            print(f"  ✓ Modified: {root_metadata.get('modifiedTime')}")
            
        except Exception as e:
            print(f"  ❌ Cannot access root folder: {e}")
            return
        
        # Now try to get the bad resource metadata
        print(f"\n🔍 Checking the problematic resource ({bad_resource_id}):")
        try:
            metadata = service.files().get(
                fileId=bad_resource_id,
                fields='id,name,mimeType,modifiedTime,parents,webViewLink,trashed,size,owners'
            ).execute()
            
            print("\n✓ Resource found! Details:")
            print(f"  ID: {metadata.get('id')}")
            print(f"  Name: {metadata.get('name')}")
            print(f"  MIME Type: {metadata.get('mimeType')}")
            print(f"  Modified: {metadata.get('modifiedTime')}")
            print(f"  Parents: {metadata.get('parents', [])}")
            print(f"  Trashed: {metadata.get('trashed', False)}")
            print(f"  Size: {metadata.get('size', 'N/A')}")
            print(f"  Web Link: {metadata.get('webViewLink')}")
            print(f"  Owners: {[owner.get('displayName', 'Unknown') for owner in metadata.get('owners', [])]}")
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"  ❌ Resource does not exist or is inaccessible")
                print(f"  This explains why your webhook is failing!")
                
                # Check if there are any recent files in the root folder
                print(f"\n📋 Let's check recent files in your root folder instead:")
                try:
                    from datetime import datetime, UTC, timedelta
                    cutoff_time = datetime.now(UTC) - timedelta(hours=24)
                    cutoff_str = cutoff_time.isoformat().replace('+00:00', 'Z')
                    
                    recent_files = service.files().list(
                        q=f"'{root_folder_id}' in parents and modifiedTime > '{cutoff_str}' and trashed = false",
                        fields='files(id,name,mimeType,modifiedTime,parents)',
                        orderBy='modifiedTime desc',
                        pageSize=10
                    ).execute()
                    
                    files = recent_files.get('files', [])
                    print(f"  Found {len(files)} files modified in last 24 hours:")
                    for i, file in enumerate(files, 1):
                        print(f"    {i}. {file.get('name')} ({file.get('id')}) - {file.get('modifiedTime')}")
                        
                except Exception as list_e:
                    print(f"  ❌ Could not list recent files: {list_e}")
            else:
                print(f"  ❌ HTTP Error: {e}")
                
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            
        # List all recent webhook activity
        print(f"\n🔔 Recommendation:")
        print(f"  The resource ID {bad_resource_id} doesn't exist.")
        print(f"  This could be:")
        print(f"  1. A stale webhook notification for a deleted file")
        print(f"  2. A webhook misconfiguration") 
        print(f"  3. You may need to re-register your webhooks")
        print(f"  4. Try uploading a new file to test current webhook behavior")
            
    except Exception as e:
        print(f"❌ Failed to initialize Google Drive service: {e}")

if __name__ == "__main__":
    debug_resource()