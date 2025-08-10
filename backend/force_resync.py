#!/usr/bin/env python3
"""
Force re-sync of a specific document by clearing its sync status
"""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

from app.rag.sync_tracker import get_sync_db, DocumentSync

def force_resync_document(source_doc_id: str):
    """Force re-sync by clearing the sync status"""
    db = next(get_sync_db())
    
    # Find the document sync record
    doc_sync = db.query(DocumentSync).filter(
        DocumentSync.source_doc_id == source_doc_id
    ).first()
    
    if doc_sync:
        # Clear sync status to force re-processing
        doc_sync.last_synced_at = None
        doc_sync.sync_status = "PENDING"
        doc_sync.error_message = None
        doc_sync.retry_count = 0
        
        db.commit()
        print(f"✅ Forced re-sync for document {source_doc_id}")
        return True
    else:
        print(f"❌ Document sync record not found for {source_doc_id}")
        return False

if __name__ == "__main__":
    # Force re-sync the income statement image
    image_doc_id = "15LTl6PcqwD0Ksrp2zTB14Jt_PWXfuVf3"
    success = force_resync_document(image_doc_id)
    
    if success:
        print("Now run ingestion again to process the image with vision enabled")
