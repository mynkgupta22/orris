from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import AuthController
from app.schemas.user import UserCreate, UserLogin
from app.schemas.auth import TokenResponse, GoogleAuthRequest, LogoutResponse
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
auth_controller = AuthController()

@router.post("/signup", response_model=TokenResponse)
async def signup(
    user_create: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Manual user signup with email and password"""
    return await auth_controller.signup(user_create, request, response, db)

@router.post("/login", response_model=TokenResponse)
async def login(
    user_login: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Manual user login with email and password"""
    return await auth_controller.login(user_login, request, response, db)

@router.post("/google", response_model=TokenResponse)
async def google_auth(
    google_request: GoogleAuthRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Google OAuth2 authentication"""
    return await auth_controller.google_auth(google_request, request, response, db)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    return await auth_controller.refresh_token(request, response, db)

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate refresh token"""
    return await auth_controller.logout(request, response, current_user, db)