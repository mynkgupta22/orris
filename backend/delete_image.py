#!/usr/bin/env python3
"""
Delete specific image from Qdrant to force re-processing with vision enabled
"""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

from app.rag.index_qdrant import get_qdrant_client

def delete_image_from_qdrant(source_doc_id: str):
    """Delete all chunks for a specific document from Qdrant"""
    client = get_qdrant_client()
    collection_name = "documents"
    
    # Delete points by source_doc_id filter
    result = client.delete(
        collection_name=collection_name,
        points_selector={
            "filter": {
                "must": [
                    {
                        "key": "source_doc_id",
                        "match": {"value": source_doc_id}
                    }
                ]
            }
        }
    )
    
    print(f"Deleted {result.status.deleted_count} points for document {source_doc_id}")
    return result.status.deleted_count

if __name__ == "__main__":
    # Delete the income statement image
    image_doc_id = "15LTl6PcqwD0Ksrp2zTB14Jt_PWXfuVf3"  # From your Qdrant data
    deleted_count = delete_image_from_qdrant(image_doc_id)
    
    if deleted_count > 0:
        print(f"✅ Successfully deleted {deleted_count} chunks for image")
        print("Now re-upload the image to Google Drive or run ingestion again")
    else:
        print("❌ No chunks found to delete")
