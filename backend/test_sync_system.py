#!/usr/bin/env python3
"""
Comprehensive test for the sync system functionality
"""
import os
import sys
import asyncio
from datetime import datetime, UTC
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_connection():
    """Test database connection and sync tracker"""
    print("🗄️  Testing Database Connection and Sync Tracker")
    
    try:
        from app.rag.sync_tracker import track_document_sync, get_documents_needing_sync
        
        # Test creating a sync record
        test_doc_id = "test-system-doc-123"
        sync_record = track_document_sync(
            test_doc_id, 
            "test_system_document.pdf", 
            datetime.now(UTC)
        )
        print(f"   ✅ Created sync record: {sync_record.source_doc_name}")
        
        # Test getting documents needing sync
        docs = get_documents_needing_sync()
        print(f"   ✅ Found {len(docs)} documents needing sync")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False


def test_vector_database():
    """Test Qdrant connection and operations"""
    print("\n🔍 Testing Vector Database Operations")
    
    try:
        # Test basic Qdrant connection
        from app.rag.index_qdrant import get_client, search_text, delete_document_chunks
        
        client = get_client()
        print("   ✅ Qdrant client connection successful")
        
        # Test search functionality
        results = search_text("test", top_k=5)
        print(f"   ✅ Search returned {len(results)} results")
        
        # Test delete functionality (with non-existent doc, should return 0)
        deleted = delete_document_chunks("non-existent-doc-id")
        print(f"   ✅ Delete function working (deleted {deleted} chunks)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Vector database test failed: {e}")
        return False


def test_google_drive_connection():
    """Test Google Drive API connection"""
    print("\n☁️  Testing Google Drive Connection")
    
    try:
        from app.rag.drive import get_drive_service
        
        service = get_drive_service()
        
        # Test basic API call
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')
        print(f"   ✅ Connected to Google Drive as: {user_email}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Google Drive test failed: {e}")
        return False


async def test_sync_service_logic():
    """Test sync service background processing logic"""
    print("\n🔄 Testing Sync Service Logic")
    
    try:
        # Test deletion processing
        from app.services.sync_service import _handle_document_deletion
        
        await _handle_document_deletion("test-deletion-doc-456")
        print("   ✅ Document deletion logic processed successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Sync service test failed: {e}")
        return False


def test_environment_config():
    """Test environment configuration"""
    print("\n⚙️  Testing Environment Configuration")
    
    required_vars = {
        'DATABASE_URL': 'Database connection string',
        'GDRIVE_ROOT_ID': 'Google Drive folder ID', 
        'GOOGLE_APPLICATION_CREDENTIALS': 'Service account credentials',
        'QDRANT_HOST': 'Qdrant host',
        'QDRANT_COLLECTION_NAME': 'Qdrant collection name'
    }
    
    all_good = True
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'CREDENTIALS' in var or 'URL' in var:
                display_value = f"{value[:20]}..." if len(value) > 20 else "***"
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: Missing ({desc})")
            all_good = False
    
    return all_good


async def main():
    """Run all tests"""
    print("🧪 Comprehensive Sync System Test Suite\n")
    
    results = []
    
    # Run all tests
    results.append(("Environment Config", test_environment_config()))
    results.append(("Database Connection", test_database_connection()))
    results.append(("Vector Database", test_vector_database()))
    results.append(("Google Drive", test_google_drive_connection()))
    results.append(("Sync Service", await test_sync_service_logic()))
    
    # Print summary
    print(f"\n{'='*50}")
    print("📊 TEST RESULTS SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! Your sync system is ready to use.")
        print("\nNext steps:")
        print("1. Set up webhooks using: python app/rag/webhook_manager.py")
        print("2. Make your FastAPI server publicly accessible")
        print("3. Register webhook with Google Drive")
        print("4. Test with real file changes in Google Drive")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please fix the issues above.")
        print("Check environment variables and service connectivity.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()