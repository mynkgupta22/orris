# RAG (Retrieval Augmented Generation) Module

This module implements the RAG system for document processing, embedding, and retrieval.

## Directory Structure

```
rag/
├── core/                   # Core RAG functionality
│   ├── chunking.py        # Text chunking and processing
│   ├── embed.py           # Embedding generation
│   ├── loaders.py         # Document loaders for different formats
│   ├── extractors.py      # Content extraction utilities
│   └── schemas.py         # Core data models and schemas
│
├── storage/               # Storage and database operations
│   ├── index_qdrant.py    # Vector database operations
│   └── sync_tracker.py    # Document sync state tracking
│
├── integrations/          # External service integrations
│   ├── drive.py          # Google Drive integration
│   ├── vision.py         # Vision API for image processing
│   └── webhook_manager.py # Webhook management system
│
├── api/                   # API endpoints and schemas
│   ├── retriever_router.py    # FastAPI routes
│   └── retriever_schemas.py   # API request/response schemas
│
├── pipeline/              # Processing pipelines
│   ├── retrieval_pipeline.py  # Main RAG retrieval pipeline
│   ├── ingest.py             # Document ingestion pipeline
│   └── access_control.py     # Access control system
│
└── config/               # Configuration
    └── config.py        # RAG module configuration
```

## Key Components

1. **Document Processing**
   - Document loading and parsing
   - Text chunking and processing
   - Embedding generation

2. **Storage**
   - Vector storage in Qdrant
   - Sync state tracking
   - Document metadata management

3. **Integration**
   - Google Drive connectivity
   - Vision API for images
   - Webhook management

4. **API**
   - RESTful endpoints
   - Request/response handling
   - Schema validation

5. **Pipeline**
   - Document ingestion
   - Retrieval augmentation
   - Access control

## Usage

```python
from app.rag.pipeline.retrieval_pipeline import RetrievalPipeline
from app.rag.core.schemas import QueryRequest

# Initialize pipeline
pipeline = RetrievalPipeline()

# Process query
response = await pipeline.retrieve_and_answer(
    query="your question",
    user=current_user
)
```

## Configuration

Key settings in `config/config.py`:
- Embedding model configuration
- Chunking parameters
- Vector store settings
- Integration credentials
