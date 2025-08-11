from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.core.config import settings
from app.routers import auth, users, webhooks
from app.rag.retriever_router import router as rag_router
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

@app.on_event("startup")
async def startup_event():
    # Start the webhook renewal service in the background
    asyncio.create_task(run_webhook_renewal_service())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)