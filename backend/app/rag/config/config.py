import os
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path


env_path = Path(__file__).parent.parent.parent.parent / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

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
    EMBEDDING_DIMENSION = 1024  # BGE-M3 embedding dimension
    
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


# Lightweight settings object for ingestion/indexing utilities that expect it
@dataclass
class QdrantSettings:
    host: str
    port: int
    api_key: str | None
    collection_name: str


def load_qdrant_config() -> QdrantSettings:
    """Compatibility helper for modules importing load_qdrant_config."""
    return QdrantSettings(
        host=Config.QDRANT_HOST,
        port=Config.QDRANT_PORT,
        api_key=os.getenv("QDRANT_API_KEY"),
        collection_name=Config.QDRANT_COLLECTION_NAME,
    )