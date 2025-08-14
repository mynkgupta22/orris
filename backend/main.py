import os
import certifi
import logging

# Configure SSL certificates before any HTTP requests
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.core.config import settings
from app.routers import auth, users, webhooks
from app.rag.api.retriever_router import router as rag_router
from app.services.webhook_renewal import run_webhook_renewal_service, ensure_webhook_initialized, migrate_json_to_database

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Orris Authentication API",
    description="Authentication and User Management Backend for EVIDEV LLP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://orris-4vg9.vercel.app'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(rag_router)

@app.get("/", tags=["root"])
async def root():
    return {"message": "Orris Authentication API is running"}

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

@app.get("/debug/cors", tags=["debug"])
async def debug_cors():
    """Debug endpoint to check CORS configuration"""
    return {
        "allowed_origins": settings.get_allowed_origins(),
        "raw_allowed_origins": settings.allowed_origins,
        "environment": settings.environment,
        "cors_config": {
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    }

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Orris API...")
    
    # # Migrate existing JSON data to database (one-time operation)
    # try:
    #     migrated_count = migrate_json_to_database()
    #     if migrated_count > 0:
    #         logger.info(f"Migrated {migrated_count} webhook channels from JSON to database")
    # except Exception as e:
    #     logger.error(f"Error during JSON to database migration: {e}")
    
    # Initialize webhooks if needed (this will create them in database)
    try:
        webhook_initialized = await ensure_webhook_initialized()
        if webhook_initialized:
            logger.info("Webhook initialization completed during startup")
        else:
            logger.info("Webhook initialization skipped (missing env vars) or failed")
    except Exception as e:
        logger.error(f"Error during webhook initialization: {e}")
    
    # Start the webhook renewal service in the background
    asyncio.create_task(run_webhook_renewal_service())

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)