# Core RAG Components

This directory contains the core functionality for the RAG system.

## Components

### chunking.py
Handles document chunking with features:
- Recursive text splitting
- Smart chunk boundaries
- Overlap management
- Token counting

### embed.py
Manages embedding generation:
- Sentence transformer integration
- Batch processing
- Cache management
- Model configuration

### loaders.py
Document loading utilities:
- PDF processing
- DOCX handling
- Text file processing
- Image extraction
- Excel parsing

### extractors.py
Content extraction tools:
- Image text extraction
- Table extraction
- Metadata extraction
- Format-specific processors

### schemas.py
Core data models:
- Document chunks
- Metadata structures
- Processing configurations
- Type definitions
