#!/usr/bin/env python3
"""
Demo script showing how the document sync functionality works.
This demonstrates the complete workflow for handling document changes.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add the parent directory to the Python path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.sync_tracker import (
    track_document_sync, 
    mark_document_synced, 
    mark_document_failed,
    document_needs_resync,
    get_documents_needing_sync
)
from app.rag.index_qdrant import delete_document_chunks
from app.models.document_sync import SyncStatus


def demo_sync_workflow():
    """Demonstrate the complete sync workflow"""
    
    print("🔄 Document Sync Workflow Demo\n")
    
    # Example document details
    doc_id = "demo_doc_12345"
    doc_name = "sample_document.pdf"
    modified_time = datetime.now(UTC)
    
    print("1. 📄 New Document Processing")
    print(f"   Document: {doc_name} (ID: {doc_id})")
    
    # Step 1: Track new document
    sync_record = track_document_sync(doc_id, doc_name, modified_time)
    print(f"   Status: {sync_record.sync_status}")
    print(f"   Created: {sync_record.created_at}")
    
    print("\n2. ✅ Document Successfully Processed")
    # Step 2: Mark as synced after successful processing
    synced_record = mark_document_synced(doc_id)
    if synced_record:
        print(f"   Status: {synced_record.sync_status}")
        print(f"   Synced: {synced_record.last_synced_at}")
    
    print("\n3. 🔍 Check if Document Needs Re-sync")
    # Step 3: Check if document needs resync (should be False since just synced)
    needs_sync = document_needs_resync(doc_id, modified_time)
    print(f"   Needs sync: {needs_sync}")
    
    print("\n4. 📝 Document Modified in Google Drive")
    # Step 4: Simulate document modification
    new_modified_time = datetime.now(UTC)
    updated_record = track_document_sync(doc_id, doc_name, new_modified_time)
    needs_sync_after_update = document_needs_resync(doc_id, new_modified_time)
    print(f"   Modified time updated: {new_modified_time}")
    print(f"   Needs sync: {needs_sync_after_update}")
    
    print("\n5. 🗑️  Document Deletion Simulation")
    # Step 5: Simulate deleting document chunks
    try:
        deleted_count = delete_document_chunks(doc_id)
        print(f"   Deleted {deleted_count} chunks from vector DB")
    except Exception as e:
        print(f"   Note: {e} (This is normal if no chunks exist yet)")
    
    print("\n6. ❌ Simulate Processing Failure")
    # Step 6: Simulate a processing failure
    failed_record = mark_document_failed(doc_id, "Connection timeout during processing")
    if failed_record:
        print(f"   Status: {failed_record.sync_status}")
        print(f"   Error: {failed_record.error_message}")
        print(f"   Retry count: {failed_record.retry_count}")
    
    print("\n7. 📋 Get Documents Needing Sync")
    # Step 7: Get all documents that need sync
    docs_needing_sync = get_documents_needing_sync()
    print(f"   Documents needing sync: {len(docs_needing_sync)}")
    for doc in docs_needing_sync:
        print(f"   - {doc.source_doc_name} ({doc.sync_status})")
    
    print("\n✅ Demo completed!")
    print("\nThis demonstrates how the sync system:")
    print("  • Tracks document processing state")
    print("  • Detects when documents need re-sync")
    print("  • Handles processing failures with retry logic")
    print("  • Manages document deletion from vector DB")


if __name__ == "__main__":
    print("Make sure to run database migrations first:")
    print("  alembic upgrade head\n")
    
    try:
        demo_sync_workflow()
    except Exception as e:
        print(f"Error running demo: {e}")
        print("\nMake sure:")
        print("1. Database is running and accessible")
        print("2. Run 'alembic upgrade head' to create the document_sync table")
        print("3. Qdrant is running (for delete testing)")