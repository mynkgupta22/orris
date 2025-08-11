# Orris Backend

This is the backend service for Orris, providing RAG (Retrieval Augmented Generation) capabilities with secure document management and chat functionality.

## Project Structure

```
backend/
├── app/               # Main application code
│   ├── controllers/   # Business logic controllers
│   ├── core/         # Core functionality and config
│   ├── models/       # Database models
│   ├── rag/          # RAG implementation
│   ├── routers/      # API routes
│   ├── schemas/      # Pydantic models
│   └── services/     # Business services
│
├── config/           # Configuration files
├── docs/            # Documentation
├── scripts/         # Utility scripts
├── tests/           # Test files
├── alembic/         # Database migrations
└── main.py          # Application entry point
```

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
- Copy `config/.env.example` to `config/.env`
- Add Google service account credentials to `config/service-account.json`

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
python main.py
```

## Development

- API documentation available at `/docs` when server is running
- Run tests with `pytest tests/`
- Use scripts in `scripts/` for common maintenance tasks

## Configuration

All configuration files are in the `config/` directory:
- `.env` - Environment variables
- `service-account.json` - Google service account credentials
- `webhook_channels.json` - Webhook configuration

## Documentation

See the `docs/` directory for detailed documentation on:
- Architecture
- API endpoints
- Integration guides
- Deployment procedures
