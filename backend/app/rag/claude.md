# TODO.md — Secure RAG Pipeline (Post-Google Drive)

## RULES

**RULES**
- Use only mutually compatible dependencies
- Implement what is needed in the most simple way, don't include unnessesary things
- Do not implement without approval
- Make sure that for testing, outputs and storage components are visible so that i can approve if things are working correctly.
- Work phase wise, only move to next when explicitly instructed to.

## Context

File Structure -

EVIDEV_DATA (Main Folder in google drive)
 ├─ NON PI        (public docs)
 └─ PI            (restricted)
     ├─ a20       (folder per user/uid)
     │   └─ File1
     ├─ a21
     └─ ...

- Files in PI/<uid>/ belong to that uid (e.g., a20) → default is_pi = true and uid = "a20".
- Files in NON PI/ → default is_pi = false (subject to override by content-scan).

Overview:

1. Fetches files from **Google Drive** (structured folder layout)
2. Processes them into **chunks** (text, tables, images with OCR)
3. Tags data as **PI** (Personally Identifiable) or **Non-PI**
4. Generates **embeddings** (Nomic)
5. Stores vectors + metadata in **Qdrant**

---

## 📥 PHASE 1 — Fetch Files from Google Drive

**Logic:**
1. Authenticate with service account JSON.
2. List files in:
- `NON PI/` folder
- `PI/<uid>/` subfolders
3. For each file:
- Download to `/tmp/<file_name>`
- Pass along **metadata**:
  ```json
  {
    "file_id": "<gd_id>",
    "file_name": "<name>",
    "mime_type": "<mime>",
    "created_at": "<timestamp>",
    "owner_email": "<owner_email>",
    "parent_folder_type": "PI" | "NON_PI",
    "uid": "<uid or null>"
  }
  ```

---

## PHASE 2 — Document Processing & Chunking

### 2.1 PDF Processing
Tools: `PyMuPDF` (`fitz`), `camelot` for tables, `tesseract` for OCR.

Steps:
- Loop through each page.
- Extract **tables** → convert to Markdown or CSV string. Each table = **1 chunk**.
- Extract **images**:
  - Save each image
  - OCR → store extracted text in chunk’s `ocr_text`
  - Mark `is_image = true`
- Extract **text** from page → clean → feed to LangChain’s `RecursiveCharacterTextSplitter`:
  - `chunk_size = 800 tokens` (~1500 chars)
  - `chunk_overlap = 50`
  - Each chunk gets `source_page` and `chunk_index`.

### 2.2 DOCX Processing
Tools: `python-docx`
- Extract paragraphs → chunk as above.
- Extract tables → Markdown → single chunk per table.

### 2.3 TXT Processing
- Read entire file → chunk as above.

### 2.4 Common Post-Processing
- Count tokens for each chunk using `tiktoken` or model tokenizer.
- Generate a unique `chunk_id` (`uuid4()`).

---

## PHASE 3 — PI Tagging & Metadata Creation

### 3.1 Base Logic
- If `parent_folder_type == PI`:
  - `is_pi = true`
  - `uid = provided_uid`
  - `access_roles = ["pi"]`
- If `parent_folder_type == NON_PI`:
  - `is_pi = false`
  - `uid = null`
  - `access_roles = ["non_pi"]`

### 3.2 PI Override for NON-PI
*(Optional, but recommended for safety)*
- Scan each chunk’s text with:
  - Regex patterns (emails, phone numbers, IDs, salaries)
  - Lightweight NER (spaCy or Presidio)
- If sensitive data found → set `is_pi = true` for that chunk.

### 3.3 Metadata Schema for Each Chunk
```json
{
  "chunk_id": "<uuid4>",
  "source_doc_id": "<file_id>",
  "source_doc_name": "<file_name>",
  "folder_type": "PI" | "NON_PI",
  "owner_email": "<owner_email>",
  "uploaded_by": "ingest_service",
  "doc_type": "pdf" | "docx" | "txt" | "image",
  "created_at": "<from upstream>",
  "ingested_at": "<now>",
  "is_pi": true | false,
  "access_roles": ["pi"] | ["non_pi"],
  "chunk_index": <int>,
  "source_page": <int>,
  "language": "en",
  "token_count": <int>,
  "is_table": true | false,
  "is_image": true | false,
  "ocr_text": "<ocr text if is_image>",
  "uid": "<uid or null>",
  "doc_url": "https://drive.google.com/file/d/<file_id>/view"
}

```

## PHASE 4 — Embedding & Storage in Qdrant

### 4.1 Embedding

Tool: nomic-embed-text

embedding = nomic_embed_text(chunk_text)  # → list[float]
For images, embed OCR text or a generated caption.

### 4.2 Storage

Tool: Qdrant (Docker)

**Setup:**
- Run Qdrant in Docker: `docker run -p 6333:6333 qdrant/qdrant`
- Create collection with vector dimension matching nomic-embed-text-v1 (768 dimensions)
- Use Cosine similarity for distance metric

**Storage Process:**
1. Connect to Qdrant client
2. For each chunk:
   - Generate embedding vector from chunk text
   - Store vector with payload containing all metadata
   - Use `chunk_id` as point ID for easy retrieval

**Collection Schema:**
```python
collection_config = {
    "vectors": {
        "size": 768,  # nomic-embed-text dimension
        "distance": "Cosine"
    }
}
```

**Point Structure:**
```python
point = {
    "id": chunk_id,
    "vector": embedding,
    "payload": metadata  # All chunk metadata from Phase 3.3
}
``` 
