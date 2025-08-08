import os
import logging
from typing import List, Dict
from config import Config
from google_drive_client import GoogleDriveClient
from document_processor import DocumentProcessor
from pi_tagger import PITagger
from embedding_storage import EmbeddingStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureRAGPipeline:
    """Main pipeline for secure RAG document processing"""
    
    def __init__(self):
        logger.info("Initializing Secure RAG Pipeline")
        
        # Validate configuration
        Config.validate()
        
        # Initialize components
        self.drive_client = GoogleDriveClient()
        self.doc_processor = DocumentProcessor()
        self.pi_tagger = PITagger()
        self.embedding_storage = EmbeddingStorage()
    
    def run_full_pipeline(self, cleanup_temp: bool = True) -> Dict:
        """Run the complete RAG pipeline"""
        logger.info("Starting full RAG pipeline execution")
        
        results = {
            'files_fetched': 0,
            'chunks_created': 0,
            'chunks_tagged': 0,
            'chunks_stored': 0,
            'errors': []
        }
        
        try:
            # PHASE 1: Fetch files from Google Drive
            logger.info("PHASE 1: Fetching files from Google Drive")
            files_metadata = self.drive_client.fetch_all_files()
            results['files_fetched'] = len(files_metadata)
            logger.info(f"Fetched {len(files_metadata)} files")
            
            all_chunks = []
            
            # PHASE 2: Process each file
            logger.info("PHASE 2: Processing documents and creating chunks")
            for file_meta in files_metadata:
                try:
                    # Download file
                    local_path = self.drive_client.download_file(
                        file_meta['file_id'], 
                        file_meta['file_name']
                    )
                    
                    # Process document
                    chunks = self.doc_processor.process_document(local_path, file_meta)
                    all_chunks.extend(chunks)
                    
                    # Clean up downloaded file
                    if cleanup_temp and os.path.exists(local_path):
                        os.remove(local_path)
                        logger.debug(f"Cleaned up {local_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to process file {file_meta['file_name']}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            results['chunks_created'] = len(all_chunks)
            logger.info(f"Created {len(all_chunks)} total chunks")
            
            # PHASE 3: Tag chunks with PI information
            logger.info("PHASE 3: Tagging chunks with PI information")
            tagged_chunks = self.pi_tagger.tag_chunks(all_chunks)
            results['chunks_tagged'] = len(tagged_chunks)
            
            # PHASE 4: Generate embeddings and store in Qdrant
            logger.info("PHASE 4: Generating embeddings and storing in Qdrant")
            storage_result = self.embedding_storage.store_chunks(tagged_chunks)
            results['chunks_stored'] = storage_result['stored']
            
            if storage_result['failed'] > 0:
                error_msg = f"Failed to store {storage_result['failed']} chunks"
                logger.warning(error_msg)
                results['errors'].append(error_msg)
            
            logger.info("Pipeline execution completed successfully")
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            raise
        
        return results
    
    def get_pipeline_status(self) -> Dict:
        """Get current pipeline status and collection info"""
        try:
            collection_info = self.embedding_storage.get_collection_info()
            drive_folders = self.drive_client.get_folder_structure()
            
            return {
                'collection_info': collection_info,
                'drive_folders': drive_folders,
                'config': {
                    'chunk_size': Config.CHUNK_SIZE,
                    'chunk_overlap': Config.CHUNK_OVERLAP,
                    'embedding_dimension': Config.EMBEDDING_DIMENSION,
                    'qdrant_collection': Config.QDRANT_COLLECTION_NAME
                }
            }
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {'error': str(e)}
    
    def search_documents(self, query: str, limit: int = 10, 
                        pi_access: bool = False, uid: str = None) -> List[Dict]:
        """Search documents with proper access control"""
        try:
            # Build access filter
            filter_conditions = {}
            
            if not pi_access:
                # Only non-PI documents
                filter_conditions['is_pi'] = False
            elif uid:
                # PI documents for specific user
                filter_conditions['uid'] = uid
            # If pi_access=True and no uid, search all PI docs (admin access)
            
            results = self.embedding_storage.search_similar(
                query, 
                limit=limit, 
                filter_conditions=filter_conditions if filter_conditions else None
            )
            
            logger.info(f"Search returned {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

def main():
    """Main function to run the pipeline"""
    try:
        # Create pipeline
        pipeline = SecureRAGPipeline()
        
        print("Secure RAG Pipeline")
        print("=" * 30)
        
        # Show status
        status = pipeline.get_pipeline_status()
        print(f"Current collection vectors: {status.get('collection_info', {}).get('vectors_count', 0)}")
        print(f"Available folders: {list(status.get('drive_folders', {}).keys())}")
        
        # Ask user what to do
        print("\nOptions:")
        print("1. Run full pipeline")
        print("2. Get pipeline status")
        print("3. Test search")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            print("\nRunning full pipeline...")
            results = pipeline.run_full_pipeline()
            
            print(f"\nPipeline Results:")
            print(f"  Files fetched: {results['files_fetched']}")
            print(f"  Chunks created: {results['chunks_created']}")
            print(f"  Chunks tagged: {results['chunks_tagged']}")
            print(f"  Chunks stored: {results['chunks_stored']}")
            
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:  # Show first 3 errors
                    print(f"    - {error}")
        
        elif choice == '2':
            print(f"\nPipeline Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
        
        elif choice == '3':
            query = input("Enter search query: ").strip()
            if query:
                results = pipeline.search_documents(query, limit=5)
                print(f"\nSearch Results ({len(results)} found):")
                for i, result in enumerate(results, 1):
                    payload = result['payload']
                    print(f"\n{i}. Score: {result['score']:.4f}")
                    print(f"   Document: {payload['source_doc_name']}")
                    print(f"   Type: {payload['doc_type']} | PI: {payload['is_pi']}")
                    print(f"   Text: {payload['text'][:100]}...")
        
        elif choice == '4':
            print("Goodbye!")
        
        else:
            print("Invalid choice")
    
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()