from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

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

@app.get("/", tags=["root"])
async def root():
    return {"message": "Orris Authentication API is running"}

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

# Placeholder routes for now (without database)
@app.post("/auth/signup", tags=["authentication"])
async def signup():
    return {"message": "Signup endpoint - database connection needed"}

@app.post("/auth/login", tags=["authentication"]) 
async def login():
    return {"message": "Login endpoint - database connection needed"}

@app.post("/auth/google", tags=["authentication"])
async def google_auth():
    return {"message": "Google auth endpoint - database connection needed"}

@app.post("/auth/refresh", tags=["authentication"])
async def refresh_token():
    return {"message": "Refresh token endpoint - database connection needed"}

@app.post("/auth/logout", tags=["authentication"])
async def logout():
    return {"message": "Logout endpoint - database connection needed"}

@app.get("/users/me", tags=["users"])
async def get_profile():
    return {"message": "Get profile endpoint - database connection needed"}

@app.put("/users/me", tags=["users"])
async def update_profile():
    return {"message": "Update profile endpoint - database connection needed"}

@app.post("/users/me/change-password", tags=["users"])
async def change_password():
    return {"message": "Change password endpoint - database connection needed"}

@app.get("/users/{user_id}", tags=["users"])
async def get_user_by_id(user_id: int):
    return {"message": f"Get user {user_id} endpoint - database connection needed"}