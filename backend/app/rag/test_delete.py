#!/usr/bin/env python3
"""
Test script for document deletion functionality.
This script demonstrates how to delete document chunks from Qdrant.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.index_qdrant import delete_document_chunks, search_text


def test_delete_functionality():
    """Test the delete_document_chunks function"""
    
    print("Testing document deletion functionality...\n")
    
    # Example document ID (you can replace this with an actual doc ID from your system)
    test_doc_id = "test_document_123"
    
    print(f"1. Searching for chunks from document: {test_doc_id}")
    
    # Search for chunks belonging to this document before deletion
    try:
        results_before = search_text(
            query="*",  # Search for anything
            top_k=100,
            eq_filter={"source_doc_id": test_doc_id}
        )
        print(f"   Found {len(results_before)} chunks before deletion")
        
        if len(results_before) == 0:
            print(f"   No chunks found for document {test_doc_id}")
            print("   You can run the ingestion script first to add some test data")
            return
            
    except Exception as e:
        print(f"   Error searching: {e}")
        return
    
    print(f"\n2. Deleting chunks from document: {test_doc_id}")
    
    # Delete the document chunks
    try:
        deleted_count = delete_document_chunks(test_doc_id)
        print(f"   Successfully deleted {deleted_count} chunks")
        
    except Exception as e:
        print(f"   Error deleting: {e}")
        return
    
    print(f"\n3. Verifying deletion...")
    
    # Verify chunks are gone
    try:
        results_after = search_text(
            query="*",
            top_k=100,
            eq_filter={"source_doc_id": test_doc_id}
        )
        print(f"   Found {len(results_after)} chunks after deletion")
        
        if len(results_after) == 0:
            print("   ✅ Deletion successful - no chunks found")
        else:
            print("   ⚠️  Warning - some chunks still exist after deletion")
            
    except Exception as e:
        print(f"   Error verifying: {e}")
        return
    
    print("\n✅ Delete functionality test completed!")


if __name__ == "__main__":
    # Check if Qdrant configuration is available
    try:
        from app.rag.config import load_qdrant_config
        config = load_qdrant_config()
        print(f"Using Qdrant at {config.host}:{config.port}")
        print(f"Collection: {config.collection_name}\n")
    except Exception as e:
        print(f"Error loading Qdrant config: {e}")
        print("Make sure your environment variables are set correctly.")
        sys.exit(1)
    
    test_delete_functionality()