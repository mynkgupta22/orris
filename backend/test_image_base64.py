#!/usr/bin/env python3
"""
Test script to verify image base64 encoding is working
"""
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

from app.rag.integrations.vision import summarize_image_with_base64
from app.rag.core.loaders import load_file_to_elements
from app.rag.core.chunking import chunk_elements

def test_image_processing():
    """Test if image base64 encoding is working end-to-end"""
    
    # Test the vision function first
    print("Testing vision function...")
    try:
        # Use an existing test image
        test_image_path = "/Users/mayank/Desktop/orris/backend/.ingest_tmp/PI/4/imvestment_portfolio.png"
        if Path(test_image_path).exists():
            summary, base64_data = summarize_image_with_base64(test_image_path)
            print(f"Summary: {summary[:100]}...")
            print(f"Base64 length: {len(base64_data) if base64_data else 0}")
        else:
            print("No test image found, skipping vision test")
            return
    except Exception as e:
        print(f"Vision function failed: {e}")
        return
    
    # Test the loader
    print("\nTesting loader...")
    try:
        base_meta = {
            "source_doc_id": "test",
            "source_doc_name": "test_image.jpg",
            "source_doc_type": "image",
            "source_doc_url": None,
            "doc_mime_type": "image/jpeg",
            "owner_uid": None,
            "uid": None,
            "roles_allowed": ["non_pi"],
            "is_pi": False,
            "folder_path": "test",
            "source_last_modified_at": None,
            "ingested_at": "2025-08-13T00:00:00Z",
            "language": "en",
        }
        
        elements = load_file_to_elements(
            test_image_path, 
            base_meta, 
            summarize_image_with_base64_fn=summarize_image_with_base64
        )
        
        print(f"Elements generated: {len(elements)}")
        for elem in elements:
            meta = elem.get("meta", {})
            if "image_base64" in meta:
                print(f"Found image_base64 in element metadata: {len(meta['image_base64'])} chars")
            else:
                print("No image_base64 in element metadata")
                print(f"Available meta keys: {list(meta.keys())}")
        
    except Exception as e:
        print(f"Loader failed: {e}")
        return
    
    # Test chunking
    print("\nTesting chunking...")
    try:
        chunks = chunk_elements(elements)
        print(f"Chunks generated: {len(chunks)}")
        for chunk in chunks:
            if hasattr(chunk.meta, 'image_base64') and chunk.meta.image_base64:
                print(f"Found image_base64 in chunk metadata: {len(chunk.meta.image_base64)} chars")
            else:
                print("No image_base64 in chunk metadata")
                print(f"Available chunk meta attrs: {[attr for attr in dir(chunk.meta) if not attr.startswith('_')]}")
    except Exception as e:
        print(f"Chunking failed: {e}")

if __name__ == "__main__":
    test_image_processing()
