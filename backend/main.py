from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.core.config import settings
from app.routers import auth, users, webhooks
from app.rag.api.retriever_router import router as rag_router
from app.services.webhook_renewal import run_webhook_renewal_service, ensure_webhook_initialized, migrate_json_to_database
import os
import certifi
import logging
import httpx

logger = logging.getLogger(__name__)

# Configure SSL certificates before any HTTP requests
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

app = FastAPI(
    title="Orris Authentication API",
    description="Authentication and User Management Backend for EVIDEV LLP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

async def keep_alive_task():
    """
    A background task that pings the /health endpoint every 14 minutes
    to prevent the Render free-tier service from spinning down.
    """
    # Render provides the public URL of the service in this env var
    render_external_url = os.getenv("RENDER_EXTERNAL_URL")

    if not render_external_url:
        logger.warning("RENDER_EXTERNAL_URL not set. Keep-alive task will not run.")
        return

    health_check_url = f"{render_external_url}/health"
    
    # Wait a moment before starting the first ping
    await asyncio.sleep(60) # Sleep for 1 minute on startup
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(health_check_url)
                response.raise_for_status()  # Raise an exception for 4xx/5xx errors
                logger.info(f"Keep-alive ping successful to {health_check_url}, status: {response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Keep-alive ping failed: {e}")
        
        # Wait for 14 minutes before the next ping (15 minutes is Render's timeout)
        await asyncio.sleep(14 * 60)


@app.on_event("startup")
async def startup_event():
    """Initialize webhooks if needed (this will create them in database)"""
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

    asyncio.create_task(keep_alive_task())


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)