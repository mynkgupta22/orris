import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import openai
import os
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingStorage:
    """Generate embeddings and store in Qdrant vector database"""
    
    def __init__(self):
        self.qdrant_client = self._init_qdrant_client()
        self._init_openai()
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self._ensure_collection_exists()
    
    def _init_qdrant_client(self) -> QdrantClient:
        """Initialize Qdrant client"""
        try:
            client = QdrantClient(
                host=Config.QDRANT_HOST,
                port=Config.QDRANT_PORT
            )
            logger.info(f"Connected to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def _init_openai(self):
        """Initialize OpenAI API"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'your-openai-api-key':
                raise ValueError("OpenAI API key not configured")
            
            openai.api_key = api_key
            logger.info("Successfully configured OpenAI API")
            
        except Exception as e:
            logger.error(f"Failed to configure OpenAI: {e}")
            raise
    
    def _ensure_collection_exists(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI text-embedding-ada-002 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection '{self.collection_name}'")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
                
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            # Truncate text if too long
            max_length = 8000  # OpenAI limit
            if len(text) > max_length:
                text = text[:max_length]
            
            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            logger.error(f"Text length: {len(text)}")
            logger.error(f"Text preview: {text[:100]}")
            raise
    
    def store_chunks(self, chunks: List[Dict]) -> Dict:
        """Store chunks with embeddings in Qdrant"""
        stored_count = 0
        failed_count = 0
        points = []
        
        logger.info(f"Storing {len(chunks)} chunks in Qdrant...")
        
        for chunk in chunks:
            try:
                # Generate embedding
                embedding_text = self._get_embedding_text(chunk)
                embedding = self.generate_embedding(embedding_text)
                
                # Create point for Qdrant
                point = PointStruct(
                    id=chunk['chunk_id'],
                    vector=embedding,
                    payload=self._prepare_payload(chunk)
                )
                points.append(point)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                failed_count += 1
        
        # Batch store points
        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Successfully stored {stored_count} chunks in Qdrant")
            except Exception as e:
                logger.error(f"Failed to batch store points: {e}")
                failed_count += stored_count
                stored_count = 0
        
        return {
            'stored': stored_count,
            'failed': failed_count,
            'total': len(chunks)
        }
    
    def _get_embedding_text(self, chunk: Dict) -> str:
        """Get text to embed (includes OCR text if available)"""
        text = chunk['text']
        
        # Include OCR text for images
        if chunk.get('is_image') and chunk.get('ocr_text'):
            text += f" [OCR: {chunk['ocr_text']}]"
        
        # Add context for tables
        if chunk.get('is_table'):
            text = f"[TABLE] {text}"
        
        return text
    
    def _prepare_payload(self, chunk: Dict) -> Dict:
        """Prepare chunk metadata as Qdrant payload"""
        # Create a clean payload with all metadata
        payload = {
            'text': chunk['text'],  # Include the actual text content
            'chunk_id': chunk['chunk_id'],
            'source_doc_id': chunk['source_doc_id'],
            'source_doc_name': chunk['source_doc_name'],
            'folder_type': chunk['folder_type'],
            'owner_email': chunk['owner_email'],
            'uploaded_by': chunk['uploaded_by'],
            'doc_type': chunk['doc_type'],
            'created_at': chunk['created_at'],
            'ingested_at': chunk['ingested_at'],
            'is_pi': chunk['is_pi'],
            'access_roles': chunk['access_roles'],
            'chunk_index': chunk['chunk_index'],
            'source_page': chunk['source_page'],
            'language': chunk['language'],
            'token_count': chunk['token_count'],
            'is_table': chunk['is_table'],
            'is_image': chunk['is_image'],
            'doc_url': chunk['doc_url'],
            'security_level': chunk['security_level'],
            'requires_auth': chunk['requires_auth'],
            'data_classification': chunk['data_classification']
        }
        
        # Add optional fields if present
        if chunk.get('uid'):
            payload['uid'] = chunk['uid']
        
        if chunk.get('ocr_text'):
            payload['ocr_text'] = chunk['ocr_text']
        
        return payload
    
    def search_similar(self, query_text: str, limit: int = 10, 
                      filter_conditions: Optional[Dict] = None) -> List[Dict]:
        """Search for similar chunks"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query_text)
            
            # Prepare search filter
            search_filter = None
            if filter_conditions:
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        ) for key, value in filter_conditions.items()
                    ]
                )
            
            # Search
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'chunk_id': result.id,
                    'score': result.score,
                    'payload': result.payload
                })
            
            logger.info(f"Found {len(formatted_results)} similar chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                'name': self.collection_name,
                'vectors_count': collection_info.vectors_count,
                'status': collection_info.status,
                'config': {
                    'vector_size': collection_info.config.params.vectors.size,
                    'distance': collection_info.config.params.vectors.distance.name
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def delete_collection(self):
        """Delete the collection (for testing/cleanup)"""
        try:
            self.qdrant_client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")

# Test function
def test_embedding_storage():
    """Test embedding and storage functionality"""
    try:
        Config.validate()
        storage = EmbeddingStorage()
        
        # Create test chunks
        test_chunks = [
            {
                'chunk_id': 'test_embed_1',
                'text': 'This is a test document about machine learning and artificial intelligence.',
                'source_doc_id': 'doc_test_1',
                'source_doc_name': 'ml_guide.pdf',
                'folder_type': 'NON_PI',
                'owner_email': 'researcher@company.com',
                'uploaded_by': 'ingest_service',
                'doc_type': 'pdf',
                'created_at': '2024-01-01T00:00:00Z',
                'ingested_at': '2024-01-01T01:00:00Z',
                'is_pi': False,
                'access_roles': ['non_pi'],
                'chunk_index': 0,
                'source_page': 1,
                'language': 'en',
                'token_count': 15,
                'is_table': False,
                'is_image': False,
                'doc_url': 'https://drive.google.com/file/d/doc_test_1/view',
                'security_level': 'PUBLIC',
                'requires_auth': False,
                'data_classification': 'PUBLIC_DATA',
                'uid': None
            },
            {
                'chunk_id': 'test_embed_2',
                'text': 'Personal information about user activities and preferences.',
                'source_doc_id': 'doc_test_2',
                'source_doc_name': 'user_profile.pdf',
                'folder_type': 'PI',
                'owner_email': 'user@company.com',
                'uploaded_by': 'ingest_service',
                'doc_type': 'pdf',
                'created_at': '2024-01-01T00:00:00Z',
                'ingested_at': '2024-01-01T01:00:00Z',
                'is_pi': True,
                'access_roles': ['pi'],
                'chunk_index': 0,
                'source_page': 1,
                'language': 'en',
                'token_count': 10,
                'is_table': False,
                'is_image': False,
                'doc_url': 'https://drive.google.com/file/d/doc_test_2/view',
                'security_level': 'HIGH',
                'requires_auth': True,
                'data_classification': 'PERSONAL_DATA',
                'uid': 'a20'
            }
        ]
        
        print("Embedding Storage Test")
        print("=" * 30)
        
        # Get collection info
        collection_info = storage.get_collection_info()
        print(f"Collection: {collection_info}")
        
        # Store chunks
        result = storage.store_chunks(test_chunks)
        print(f"\nStorage Result:")
        print(f"  Stored: {result['stored']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Total: {result['total']}")
        
        # Test search
        print(f"\nTesting search...")
        search_results = storage.search_similar("machine learning", limit=5)
        print(f"Found {len(search_results)} results for 'machine learning'")
        
        for result in search_results:
            print(f"  Score: {result['score']:.4f}")
            print(f"  Chunk: {result['payload']['source_doc_name']}")
            print(f"  Text: {result['payload']['text'][:50]}...")
        
        # Test filtered search (non-PI only)
        print(f"\nTesting filtered search (non-PI only)...")
        filtered_results = storage.search_similar(
            "artificial intelligence",
            limit=5,
            filter_conditions={'is_pi': False}
        )
        print(f"Found {len(filtered_results)} non-PI results")
        
        # Updated collection info
        updated_info = storage.get_collection_info()
        print(f"\nUpdated collection info:")
        print(f"  Vectors: {updated_info.get('vectors_count', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_embedding_storage()