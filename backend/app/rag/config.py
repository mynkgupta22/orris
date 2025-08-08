import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google Drive
    GOOGLE_SERVICE_ACCOUNT_PATH = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    EVIDEV_DATA_FOLDER_ID = os.getenv('EVIDEV_DATA_FOLDER_ID')
    
    # Qdrant
    QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
    QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))
    QDRANT_COLLECTION_NAME = os.getenv('QDRANT_COLLECTION_NAME', 'orris_rag')
    
    # Nomic
    NOMIC_API_KEY = os.getenv('NOMIC_API_KEY')
    
    # Processing
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 800))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 50))
    TEMP_DIR = os.getenv('TEMP_DIR', '/tmp')
    
    # Embedding
    EMBEDDING_DIMENSION = 768  # nomic-embed-text dimension
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = [
            'GOOGLE_SERVICE_ACCOUNT_PATH',
            'EVIDEV_DATA_FOLDER_ID',
            'NOMIC_API_KEY'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True