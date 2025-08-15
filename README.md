# Orris - Enterprise Document Intelligence Platform

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/TypeScript-5.0+-blue.svg" alt="TypeScript Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.116+-green.svg" alt="FastAPI Version" />
  <img src="https://img.shields.io/badge/Next.js-14+-black.svg" alt="Next.js Version" />
  <img src="https://img.shields.io/badge/Status-Production-brightgreen.svg" alt="Status" />
</div>

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Security & Compliance](#security--compliance)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Monitoring & Logging](#monitoring--logging)
- [Support](#support)

## 🚀 Overview

**Orris** is an enterprise-grade Document Intelligence Platform that transforms how organizations interact with their knowledge base. Built for **EVIDEV LLP**, Orris provides a sophisticated AI-powered chatbot interface that enables users to query company documents while maintaining strict access controls and data security.

The platform automatically synchronizes with Google Drive, processes documents using advanced NLP techniques, and provides contextual responses through a secure RAG (Retrieval-Augmented Generation) system.

### 🎯 Purpose

Orris serves as an intelligent knowledge management system that:
- **Democratizes Information Access**: Enables natural language queries across company documentation
- **Enforces Data Governance**: Implements role-based access control with PI (Personal Information) protection
- **Automates Document Processing**: Real-time synchronization and intelligent content extraction
- **Enhances Productivity**: Instant answers to complex queries with source attribution

## ✨ Key Features

### 🔐 Advanced Authentication & Authorization
- **Multi-provider Authentication**: OAuth2 with Google, traditional email/password
- **Role-Based Access Control (RBAC)**: Granular permissions for document access
- **JWT Token Management**: Secure access and refresh token handling
- **Session Monitoring**: Real-time user session tracking and security

### 📄 Intelligent Document Processing
- **Real-time Synchronization**: Google Drive webhook integration for instant updates
- **Multi-format Support**: PDF, DOCX, TXT and IMAGES
- **Smart Chunking**: Advanced text segmentation for optimal retrieval
- **Vision AI Integration**: Image and diagram understanding with Gemini 2.5

### 🧠 RAG (Retrieval-Augmented Generation) System
- **Vector Search**: Qdrant-powered semantic search with BGE-M3 embeddings
- **Contextual Responses**: Gemini 2.5/Fin-Llama powered responses with source attribution
- **Access Control**: Document-level permissions enforcement
- **Audit Trail**: Comprehensive query and response logging

### 🛡️ Enterprise Security
- **Data Classification**: Folder-based PI/Non-PI content identification
- **Secure Processing**: Secure temporary storage and processing
- **Compliance Ready**: Audit logs and access controls for regulatory compliance
- **Basic Protection**: CORS and request validation

### 🔄 Real-time Operations
- **Webhook Management**: Automated Google Drive change notifications
- **Background Processing**: Asynchronous document ingestion and updates
- **Health Monitoring**: Comprehensive system health checks
- **Auto-recovery**: Intelligent error handling and retry mechanisms

## 🏗️ Architecture

```mermaid
sequenceDiagram
    participant Admin as 👨‍💼 Admin User
    participant Drive as 📁 Google Drive
    participant Webhook as 🔗 Webhook Service
    participant TaskQueue as 📋 Task Queue
    participant DocProcessor as 📄 Doc Processor
    participant Vector as 🔍 Qdrant Vector DB
    participant User as 👤 End User
    participant Frontend as 🌐 Next.js Frontend
    participant Auth as 🔐 Auth Service
    participant GoogleOAuth as 🔑 Google OAuth
    participant RAG as 🧠 RAG Pipeline
    participant LLM as 🤖 Gemini 2.5/Fin-Llama
    participant DB as 🗄️ PostgreSQL
    participant AuditLog as 📝 Audit Logger

    %% Document Addition Flow
    Note over Admin, Vector: 📋 PHASE 1: Document Addition & Processing
    Admin->>Drive: 1. Upload new document
    Drive->>Webhook: 2. Send webhook notification
    Note right of Webhook: Event: file.created<br/>File: company-policy.pdf
    
    Webhook->>Webhook: 3. Validate webhook signature
    Webhook->>TaskQueue: 4. Queue document processing task
    Note right of TaskQueue: Task: process_document<br/>File ID: 1a2b3c4d5e
    
    TaskQueue->>DocProcessor: 5. Start processing document
    DocProcessor->>Drive: 6. Download document content
    DocProcessor->>DocProcessor: 7. Extract text & metadata
    Note right of DocProcessor: Content: "Employee handbook..."<br/>Type: PDF<br/>Size: 2.5MB
    
    DocProcessor->>DocProcessor: 8. Detect PI/Non-PI content
    Note right of DocProcessor: Classification: Non-PI<br/>Access Level: General
    
    DocProcessor->>DocProcessor: 9. Chunk document
    Note right of DocProcessor: Chunks: 23<br/>Size: 800 chars each
    
    DocProcessor->>Vector: 10. Generate & store embeddings
    DocProcessor->>DB: 11. Store document metadata
    Note right of DB: Status: Processed<br/>Indexed: True<br/>Access: Non-PI
    
    %% User Authentication Flow
    Note over User, DB: � PHASE 2: User Authentication
    User->>Frontend: 12. Visit chat page
    Frontend->>Frontend: 13. Check authentication status
    Frontend->>User: 14. Show login screen
    
    User->>Frontend: 15. Click "Login with Google"
    Frontend->>GoogleOAuth: 16. Redirect to Google OAuth
    GoogleOAuth->>User: 17. Show Google consent screen
    User->>GoogleOAuth: 18. Grant permissions
    
    GoogleOAuth->>Frontend: 19. Redirect with auth code
    Frontend->>Auth: 20. Send auth code to backend
    Auth->>GoogleOAuth: 21. Exchange code for tokens
    GoogleOAuth->>Auth: 22. Return access & refresh tokens
    
    Auth->>Auth: 23. Validate user permissions
    Note right of Auth: Email: user@company.com<br/>Domain: company.com<br/>Access Level: Non-PI
    
    Auth->>DB: 24. Store/update user session
    Auth->>Auth: 25. Generate JWT tokens
    Auth->>Frontend: 26. Return JWT & user info
    
    Frontend->>Frontend: 27. Store tokens & update state
    Frontend->>User: 28. Show chat interface
    
    %% Query and Response Flow
    Note over User, AuditLog: 🧠 PHASE 3: Query Processing & Response
    User->>Frontend: 29. Type query: "What is the vacation policy?"
    Frontend->>Auth: 30. Validate JWT token
    Auth->>Auth: 31. Check token expiry & permissions
    Auth->>Frontend: 32. Token valid - proceed
    
    Frontend->>RAG: 33. Send query with auth headers
    RAG->>Auth: 34. Verify user access level
    Note right of Auth: User Level: Non-PI<br/>Query Access: Granted
    
    RAG->>AuditLog: 35. Log query attempt
    Note right of AuditLog: User: user@company.com<br/>Query: "vacation policy"<br/>Timestamp: 2025-08-15T10:30:00Z
    
    RAG->>RAG: 36. Generate query embeddings
    RAG->>Vector: 37. Perform semantic search
    Note right of Vector: Search: vacation policy<br/>Results: 5 chunks<br/>Relevance: 0.85-0.92
    
    Vector->>RAG: 38. Return relevant chunks
    RAG->>RAG: 39. Filter by user access level
    Note right of RAG: Filtered: 5 chunks<br/>All Non-PI content<br/>Access: Allowed
    
    RAG->>RAG: 40. Build context prompt
    Note right of RAG: Context: 3,200 chars<br/>Sources: 2 documents<br/>Chunks: 5
    
    RAG->>LLM: 41. Send prompt to Gemini 2.5/Fin-Llama
    Note right of LLM: Model: Gemini 2.5/Fin-Llama 33B<br/>Max tokens: 1000<br/>Temperature: 0.1
    
    LLM->>RAG: 42. Return generated response
    RAG->>RAG: 43. Format response with sources
    Note right of RAG: Response: 450 chars<br/>Sources: 2 docs<br/>Confidence: High
    
    RAG->>AuditLog: 44. Log successful response
    Note right of AuditLog: Status: Success<br/>Response time: 2.3s<br/>Sources used: 2
    
    RAG->>Frontend: 45. Return formatted response
    Frontend->>User: 46. Display response with sources
    
    %% Background Maintenance
    Note over Webhook, Vector: 🔧 PHASE 4: Background Maintenance
    loop Every 6 days
        Webhook->>Drive: 47. Renew webhook subscriptions
        Drive->>Webhook: 48. Confirm renewal
    end
    
    loop Daily
        Vector->>Vector: 49. Optimize vector indices
        DB->>DB: 50. Clean old session data
    end
    
    %% Error Handling Examples
    Note over User, AuditLog: ⚠️ ERROR SCENARIOS
    
    alt Invalid JWT Token
        Frontend->>Auth: Validate expired token
        Auth->>Frontend: Token expired
        Frontend->>Auth: Refresh token request
        Auth->>Frontend: New JWT token
    end
    
    alt Insufficient Permissions
        RAG->>Auth: Check access for PI document
        Auth->>RAG: Access denied - insufficient level
        RAG->>AuditLog: Log access denied
        RAG->>Frontend: Return permission error
    end
    
    alt Document Processing Failure
        DocProcessor->>DocProcessor: Failed to extract content
        DocProcessor->>DB: Mark document as failed
        DocProcessor->>TaskQueue: Retry after 5 minutes
    end

    %% Styling
    Note over Admin, AuditLog: 🎯 Complete Event Flow: Document → Auth → Query → Response
```

### System Components

#### Frontend (Next.js 14)
- **Modern React Interface**: TypeScript, Tailwind CSS, Radix UI
- **Real-time Chat**: WebSocket-like streaming responses
- **Responsive Design**: Mobile-first, accessible UI
- **State Management**: Zustand for efficient state handling

#### Backend (FastAPI)
- **High-Performance API**: Async/await, type hints, automatic docs
- **Microservice Architecture**: Modular design with clear separation
- **Database Layer**: SQLAlchemy with async PostgreSQL
- **Background Tasks**: Celery-like task processing

#### AI/ML Pipeline
- **Embedding Generation**: BGE-M3 for multilingual support
- **Vector Storage**: Qdrant for high-performance similarity search
- **LLM Integration**: Gemini 2.5/Fin-Llama for response generation
- **Document Processing**: Unstructured.io for content extraction

## 🛠️ Technology Stack

### Backend Technologies
| Component | Technology | Version / Notes | Purpose |
|-----------|------------|-----------------|---------|
| **API Framework** | FastAPI | 0.116.x (requirements.txt) | High-performance async API |
| **Language** | Python | 3.11+ | Core backend development |
| **Database** | PostgreSQL | 14+ | Primary data storage |
| **Vector DB** | Qdrant | 1.15.x | Semantic search and embeddings |
| **ORM** | SQLAlchemy | 2.x | Database abstraction layer |
| **Authentication** | OAuth2 + JWT | Built-in + Google OAuth helpers | Secure user authentication |
| **Task Queue** | FastAPI BackgroundTasks | Built-in FastAPI background processing | Async processing for webhooks/docs |
| **Web Server** | Uvicorn | 0.35.x | ASGI server |

### Frontend Technologies
| Component | Technology | Version / Notes | Purpose |
|-----------|------------|-----------------|---------|
| **Framework** | Next.js | 15.2.4 (package.json) | React-based frontend framework |
| **Language** | TypeScript | 5.x | Type-safe development |
| **Styling** | Tailwind CSS | 3.x | Utility-first CSS framework |
| **UI Components** | shadcn / Radix UI | Radix primitives + shadcn patterns | Accessible component library (components in `components/ui`) |
| **State Management** | Zustand | ^5 | Lightweight state management |
| **Icons / UI helpers** | Lucide, CVA, clsx | - | Iconography & variant styling |

### AI/ML Technologies
| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Gemini 2.5/Fin-Llama | Response generation |
| **Embeddings** | BGE-M3 | Multilingual text embeddings |
| **Vision AI** | Gemini 2.5 | Image and diagram processing |
| **Text Processing** | LangChain & unstructured | Document processing pipeline |
| **Vector Search** | Qdrant | Semantic similarity search |

### Infrastructure & DevOps
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Application containerization |
| **Deployment** | Frontend: Vercel; Backend: Render | Hosting platforms (see Deployment section)
| **CI/CD** | GitHub Actions | Automated deployment |
| **Monitoring** | Custom logging / external services | Application monitoring and alerting |
| **Security** | TLS / OAuth / JWT | Transport security and auth

## 🔒 Security & Compliance

### Authentication & Authorization
- **Multi-Factor Authentication**: OAuth2 with Google + JWT tokens
- **Role-Based Access Control**: Three-tier access system (Signed Up, Non-PI, PI Access)
- **Session Management**: Secure refresh token rotation
- **API Security**: Rate limiting, CORS protection, request validation

### Data Protection
- **Classification System**: Automatic PI/Non-PI content identification
- **Access Controls**: Document-level permissions enforcement
- **Audit Trail**: Comprehensive logging of all user interactions
- **Data Encryption**: TLS 1.3 for data in transit, encrypted storage

### Compliance Features
- **Audit Logging**: Complete query and response tracking
- **Access Monitoring**: Real-time user activity monitoring
- **Data Governance**: Automated compliance reporting
- **Privacy Controls**: GDPR-compliant data handling

## 📦 Installation

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Docker & Docker Compose** (recommended)
- **Google Cloud Project** with Drive API enabled

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/mynkgupta22/orris.git
cd orris

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the entire stack
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Manual Installation

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# or
pnpm install

# Start development server
npm run dev
# or
pnpm dev
```

## ⚙️ Configuration

### Environment Variables

#### Backend Configuration (.env)

```bash
# Application Settings
APP_NAME="Orris Authentication API"
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/orris

# JWT Configuration
JWT_SECRET_KEY=your-super-secure-secret-key
JWT_REFRESH_SECRET_KEY=your-refresh-secret-key
JWT_ALGORITHM=HS512
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth2
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

# Google Drive Integration
GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id
GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
EVIDEV_DATA_FOLDER_ID=your-evidev-folder-id

# Google AI/Gemini
GOOGLE_AI_API_KEY=your-google-ai-api-key
GEMINI_MODEL=gemini-2.5-flash
FIN_LLAMA_ENDPOINT=your-fin-llama-endpoint

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=orris_rag

# Embeddings
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBED_BATCH_SIZE=8

# Document Processing
CHUNK_SIZE=800
CHUNK_OVERLAP=50
TEMP_DIR=/tmp

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
GOOGLE_WEBHOOK_TOKEN=your-webhook-token
GDRIVE_ROOT_ID=your-root-folder-id

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

#### Frontend Configuration (.env.local)

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id

# Environment
NODE_ENV=production
```

### Google Drive API Setup

1. **Create Google Cloud Project**
   ```bash
   # Visit Google Cloud Console
   # Create new project or select existing
   # Enable Google Drive API
   ```

2. **Set up Service Account**
   ```bash
   # Create service account
   # Download JSON credentials
   # Share target Drive folder with service account email
   ```

3. **Configure OAuth2**
   ```bash
   # Set up OAuth2 credentials
   # Add authorized redirect URIs
   # Copy client ID and secret
   ```

### Database Setup

```bash
# Create database
createdb orris

# Run migrations
cd backend
alembic upgrade head

# Create initial admin user (optional)
python scripts/create_admin.py
```

### Vector Database Setup

```bash
# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant

# Or install locally
# Follow Qdrant installation guide
```

## 🚀 Deployment

### Production Deployment

#### Backend (Render)

Render is used to host the backend service. You can deploy the `backend/` either as a Docker service or directly from the repository.

Quick steps (Docker-based render service):

1. Create a new Web Service in Render and connect your GitHub/GitLab repository.
2. Set the root or Dockerfile to `./backend/Dockerfile` and choose the Docker plan.
3. Add environment variables in the Render dashboard (DATABASE_URL, JWT secrets, GOOGLE_* keys, QDRANT config, etc.).
4. Set the start command to:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. Run database migrations (one-off job or from Render Shell):

```bash
alembic upgrade head
```

Notes:
- Use Render Environment settings to securely store secrets.
- For scheduled jobs (webhook renewal, index optimization), create Render Cron Jobs or one-off Jobs as needed.

#### Frontend (Vercel - Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel

# Configure environment variables in Vercel dashboard
```

#### Full Stack with Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/orris
    depends_on:
      - db
      - qdrant

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
    ports:
      - "3000:3000"

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: orris
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  qdrant_data:
```

### Monitoring & Health Checks

```bash
# Health check endpoints
GET /health              # Basic health check
GET /health/detailed     # Detailed system status
GET /webhooks/status     # Webhook system status
```

## 📚 API Documentation

### Authentication Endpoints

```http
POST /auth/signup       # User registration
POST /auth/login        # User login
POST /auth/google       # Google OAuth login
POST /auth/refresh      # Token refresh
POST /auth/logout       # User logout
```

### User Management

```http
GET  /users/me          # Get current user profile
PUT  /users/me          # Update user profile
GET  /users/me/sessions # Get user sessions
```

### RAG System

```http
POST /rag/query         # Submit query to RAG system
GET  /rag/sessions      # Get chat sessions
POST /rag/sessions      # Create new chat session
GET  /rag/sessions/{id} # Get specific session
```

### Webhook Management

```http
POST /webhooks/google-drive  # Google Drive webhook endpoint
GET  /webhooks/status        # Webhook system status
```

### Interactive API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔧 Development

### Development Setup

```bash
# Backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend development
cd frontend
npm install
npm run dev

# Run tests
cd backend && pytest
cd frontend && npm test
```

### Code Quality

```bash
# Backend linting
flake8 app/
black app/
isort app/

# Frontend linting
npm run lint
npm run type-check
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing

```bash
# Backend tests
pytest app/tests/

# Frontend tests
npm run test

# Integration tests
npm run test:e2e
```

## 📊 Monitoring & Logging

### Application Monitoring

- **Health Checks**: Automated system health monitoring
- **Performance Metrics**: Response time and throughput tracking
- **Error Tracking**: Comprehensive error logging and alerting
- **Usage Analytics**: User interaction and query analytics

### Logging Structure

```python
# Log levels and categories
INFO  - Normal operations
WARN  - Potential issues
ERROR - System errors
DEBUG - Development debugging

# Log categories
auth.*     - Authentication events
rag.*      - RAG system operations
webhook.*  - Webhook processing
sync.*     - Document synchronization
```

### Key Metrics

- **Query Response Time**: Average response time for RAG queries
- **Document Sync Rate**: Documents processed per hour
- **User Engagement**: Active users and session duration
- **System Health**: Database connections, memory usage, CPU



## 📞 Support

### Getting Help

- **Documentation**: Comprehensive guides and API reference
- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Community discussions and Q&A

### Contact Information
- **Contributor 1**: Aditya Sebastian | [Email](mailto:aditya268244@gmil.com)
- **Contributor 2**: Mayank Gupta | [Email](mailto:mayankmk22@gmail.com)


<div align="center">
  <p><strong>Built with ❤️ for EVIDEV LLP</strong></p>
  <p>Transforming how organizations interact with their knowledge</p>
</div>