# In file: main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio
import json
from datetime import datetime

# --- Correctly import all necessary components ---
from app.core.config import settings # Assuming this is your settings config
from app.core.paths import WEBHOOK_CHANNELS_PATH # We need this to know where the file is
from app.routers import auth, users, webhooks
from app.services.sync_service import setup_drive_webhook
from app.rag.api.retriever_router import router as rag_router
from app.services.webhook_renewal import run_webhook_renewal_service

app = FastAPI(
    title="Orris Authentication API",
    description="Authentication and User Management Backend for EVIDEV LLP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include all your API routers ---
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(rag_router)

# --- Root and Health Check Endpoints ---
@app.get("/", tags=["root"])
async def root():
    return {"message": "Orris Authentication API is running"}

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


# --- THIS IS THE FINAL, CORRECTED STARTUP FUNCTION ---
@app.on_event("startup")
async def startup_event():
    # 1. Ensure the channels file exists (self-healing)
    if not WEBHOOK_CHANNELS_PATH.exists():
        print("webhook_channels.json not found, creating a new empty file.")
        WEBHOOK_CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(WEBHOOK_CHANNELS_PATH, 'w') as f:
            json.dump([], f)

    # 2. Set up the webhook for the main folder
    # NOTE: It's better to get this from config/env, but hardcoding is ok for the demo
    main_folder_id = "1NmJmAGWP4TMIzw4Algfl5OkiWgYdsfgh" 
    
    if main_folder_id:
        print(f"Ensuring webhook is active for main folder: {main_folder_id}")
        try:
            # Call the function to create the webhook
            new_channel_info = setup_drive_webhook(folder_id=main_folder_id)
            
            # --- THIS IS THE REAL CODE TO REPLACE THE PLACEHOLDER ---
            # It loads existing channels, adds the new one, and saves back to the file
            with open(WEBHOOK_CHANNELS_PATH, 'r+') as f:
                channels = json.load(f)
                # Remove any old channel for this folder to avoid duplicates
                channels = [c for c in channels if c.get('folder_id') != main_folder_id]
                # Add the new, active channel information
                channels.append({
                    "folder_id": main_folder_id,
                    "channel_id": new_channel_info.get('id'),
                    "resource_id": new_channel_info.get('resourceId'),
                    "expiration": new_channel_info.get('expiration'),
                    "status": "active",
                    "updated_at": datetime.now().isoformat()
                })
                f.seek(0) # Rewind file to the beginning before writing
                json.dump(channels, f, indent=2)
                f.truncate() # Remove any leftover old data if the new file is shorter
            # ---------------------------------------------------------

            print(f"Successfully set up and saved webhook for main folder: {main_folder_id}")
        except Exception as e:
            print(f"Failed to set up main webhook: {e}")
    else:
        print("WARNING: EVIDEV_DATA_FOLDER_ID is not set. No webhooks will be created.")

    # 3. Start the background renewal service
    asyncio.create_task(run_webhook_renewal_service())


# --- Google Site Verification Endpoint ---
@app.get(
    "/google-verification.html",
    response_class=HTMLResponse,
    include_in_schema=False
)
async def google_site_verification():
    """
    Serves the Google site verification file to prove ownership of the domain.
    """
    google_verification_meta_tag = '<meta name="google-site-verification" content="c-uiWfbOWxLZCIgQtRBQCyqRD9ApWbj8P82OH_Mdlqo" />'
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head><title>Google Site Verification</title>{google_verification_meta_tag}</head>
        <body>Google Site Verification File</body>
    </html>
    """
    return HTMLResponse(content=html_content)