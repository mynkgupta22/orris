#!/usr/bin/env python3
"""
Test script for Google Drive webhook functionality.
This script simulates webhook notifications and tests the complete sync pipeline.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, UTC
import requests
from unittest.mock import MagicMock

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.sync_service import process_drive_change_notification
from app.rag.sync_tracker import track_document_sync, get_documents_needing_sync


def test_webhook_endpoint():
    """Test the webhook endpoint with simulated Google Drive notifications"""
    print("🧪 Testing Webhook Endpoint\n")
    
    # Check if server is running
    webhook_url = "http://localhost:8001/webhooks/google-drive"
    status_url = "http://localhost:8001/webhooks/google-drive/status"
    
    print(f"Testing webhook status endpoint: {status_url}")
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            print("✅ Webhook endpoint is accessible")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach webhook endpoint: {e}")
        print("   Make sure the FastAPI server is running on localhost:8001")
        return False
    
    # Test webhook with simulated notification
    print(f"\nTesting webhook notification: {webhook_url}")
    
    # Simulate Google Drive webhook headers and payload
    headers = {
        "X-Goog-Channel-Id": "test-channel-123",
        "X-Goog-Channel-Token": os.getenv("GOOGLE_WEBHOOK_TOKEN", "orris-webhook-token"),
        "X-Goog-Resource-Id": "test-resource-456",
        "X-Goog-Resource-State": "update",
        "X-Goog-Message-Number": "1",
        "Content-Type": "application/json"
    }
    
    payload = {
        "kind": "drive#channel",
        "id": "test-channel-123",
        "resourceId": "test-resource-456",
        "type": "web_hook"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Webhook accepted notification")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Webhook rejected notification: {response.status_code}")
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send webhook notification: {e}")
        return False
    
    return True


async def test_background_processing():
    """Test the background processing logic"""
    print("\n🔄 Testing Background Processing\n")
    
    # Test document update processing
    print("1. Testing document update notification...")
    try:
        await process_drive_change_notification(
            channel_id="test-channel-123",
            resource_state="update",
            resource_id="test-doc-789",
            message_number="1"
        )
        print("✅ Update notification processed")
    except Exception as e:
        print(f"❌ Update processing failed: {e}")
    
    # Test document deletion processing
    print("\n2. Testing document deletion notification...")
    try:
        await process_drive_change_notification(
            channel_id="test-channel-123",
            resource_state="remove",
            resource_id="test-doc-delete-123",
            message_number="2"
        )
        print("✅ Deletion notification processed")
    except Exception as e:
        print(f"❌ Deletion processing failed: {e}")


def test_sync_tracker():
    """Test the document sync tracking functionality"""
    print("\n📋 Testing Sync Tracker\n")
    
    # Test creating sync records
    test_doc_id = "test-tracker-doc-456"
    test_doc_name = "test_document.pdf"
    modified_time = datetime.now(UTC)
    
    print(f"1. Creating sync record for: {test_doc_name}")
    try:
        sync_record = track_document_sync(test_doc_id, test_doc_name, modified_time)
        print(f"✅ Sync record created: {sync_record.sync_status}")
    except Exception as e:
        print(f"❌ Failed to create sync record: {e}")
        return
    
    # Test getting documents needing sync
    print("\n2. Getting documents needing sync...")
    try:
        docs_needing_sync = get_documents_needing_sync()
        print(f"✅ Found {len(docs_needing_sync)} documents needing sync")
        for doc in docs_needing_sync[-3:]:  # Show last 3
            print(f"   - {doc.source_doc_name} ({doc.sync_status})")
    except Exception as e:
        print(f"❌ Failed to get documents needing sync: {e}")


def test_environment_setup():
    """Test environment configuration"""
    print("🔧 Testing Environment Setup\n")
    
    required_vars = {
        "GDRIVE_ROOT_ID": "Google Drive root folder ID",
        "GOOGLE_APPLICATION_CREDENTIALS": "Path to service account JSON",
        "WEBHOOK_BASE_URL": "Public webhook URL",
        "GOOGLE_WEBHOOK_TOKEN": "Webhook verification token"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "CREDENTIALS" in var or "TOKEN" in var:
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set ({description})")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing {len(missing_vars)} required environment variables")
        print("   Set these variables before running webhook tests")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True


def show_webhook_setup_instructions():
    """Show instructions for setting up webhooks"""
    print("\n📝 Webhook Setup Instructions\n")
    
    print("1. 🌐 Make your webhook publicly accessible:")
    print("   - Deploy your FastAPI app to a public server")
    print("   - Use ngrok for local testing: `ngrok http 8001`")
    print("   - Set WEBHOOK_BASE_URL to your public URL")
    
    print("\n2. 🔐 Configure environment variables:")
    print("   export WEBHOOK_BASE_URL=https://your-domain.com")
    print("   export GOOGLE_WEBHOOK_TOKEN=your-secret-token")
    print("   export GDRIVE_ROOT_ID=your-drive-folder-id")
    
    print("\n3. 🚀 Set up the webhook:")
    print("   python app/rag/webhook_manager.py")
    
    print("\n4. 🧪 Test the setup:")
    print("   python app/rag/test_webhook.py")
    
    print("\n5. 📊 Monitor webhook activity:")
    print("   Check server logs for webhook notifications")
    print("   Monitor sync status in document_sync table")


async def main():
    """Main test function"""
    print("🔄 Google Drive Webhook Test Suite\n")
    
    # Test environment setup
    if not test_environment_setup():
        print("\n❌ Environment setup incomplete")
        show_webhook_setup_instructions()
        return
    
    # Test webhook endpoint
    if not test_webhook_endpoint():
        print("\n❌ Webhook endpoint tests failed")
        return
    
    # Test sync tracker
    test_sync_tracker()
    
    # Test background processing (if database is available)
    try:
        await test_background_processing()
    except Exception as e:
        print(f"\n⚠️  Background processing test skipped: {e}")
        print("   Make sure database is running and migrations are applied")
    
    print("\n🎉 Webhook tests completed!")
    print("\nNext steps:")
    print("1. Set up actual Google Drive webhooks using webhook_manager.py")
    print("2. Test with real file changes in Google Drive")
    print("3. Monitor sync status in document_sync table")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()