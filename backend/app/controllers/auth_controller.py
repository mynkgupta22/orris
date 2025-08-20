from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.user_log import UserLog, UserAction
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.auth import TokenResponse, GoogleAuthRequest, LogoutResponse
from app.core.security import SecurityService
from app.core.dependencies import get_client_ip, get_user_agent
from app.services.google_oauth import GoogleOAuthService
from app.core.config import settings


class AuthController:
    def __init__(self):
        self.google_oauth = GoogleOAuthService()

    async def signup(
        self,
        user_create: UserCreate,
        request: Request,
        response: Response,
        db: AsyncSession
    ) -> TokenResponse:
        """User signup with email and password"""
        
        # Validate password strength
        is_strong, message = SecurityService.validate_password_strength(user_create.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_create.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Create new user
        hashed_password = SecurityService.get_password_hash(user_create.password)
        new_user = User(
            name=user_create.name,
            email=user_create.email,
            password=hashed_password,
            role=UserRole.SIGNED_UP,
            status=UserStatus.ACTIVE,
            email_verified=False
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create tokens
        access_token = SecurityService.create_access_token({
            "sub": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role
        })
        
        refresh_token = SecurityService.create_refresh_token()
        refresh_token_hash = SecurityService.hash_token(refresh_token)
        
        # Store refresh token
        db_refresh_token = RefreshToken(
            user_id=new_user.id,
            token_hash=refresh_token_hash,
            device_id=SecurityService.generate_device_id(),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        )
        
        db.add(db_refresh_token)
        
        # Log the signup
        user_log = UserLog(
            user_id=new_user.id,
            action=UserAction.SIGNUP,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        db.add(user_log)
        await db.commit()
        
        # Set cookies
        self._set_auth_cookies(response, access_token, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(new_user).dict()
        )

    async def login(
        self,
        user_login: UserLogin,
        request: Request,
        response: Response,
        db: AsyncSession
    ) -> TokenResponse:
        """User login with email and password with enhanced security"""
        
        client_ip = get_client_ip(request)
        
        # Validate email format
        if not SecurityService.validate_email_format(user_login.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if account is locked
        if SecurityService.is_account_locked(user_login.email):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to failed login attempts"
            )
        
        # Find user
        result = await db.execute(select(User).where(User.email == user_login.email))
        user = result.scalar_one_or_none()
        
        if not user or not user.password:
            SecurityService.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not SecurityService.verify_password(user_login.password, user.password):
            SecurityService.record_failed_attempt(client_ip)
            # Lock account after 5 failed attempts
            failed_attempts = len(SecurityService._failed_login_attempts.get(client_ip, []))
            if failed_attempts >= 4:  # This will be the 5th attempt
                SecurityService.lock_account(user_login.email, duration_minutes=30)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        # Clear failed attempts on successful login
        SecurityService.clear_failed_attempts(client_ip)
        
        # Create tokens
        access_token = SecurityService.create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        refresh_token = SecurityService.create_refresh_token()
        refresh_token_hash = SecurityService.hash_token(refresh_token)
        
        # Store refresh token
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            device_id=SecurityService.generate_device_id(),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        )
        
        db.add(db_refresh_token)
        
        # Log the login
        user_log = UserLog(
            user_id=user.id,
            action=UserAction.LOGIN,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        db.add(user_log)
        await db.commit()
        
        # Set cookies
        self._set_auth_cookies(response, access_token, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user).dict()
        )

    async def google_auth(
        self,
        google_request: GoogleAuthRequest,
        request: Request,
        response: Response,
        db: AsyncSession
    ) -> TokenResponse:
        """Google OAuth authentication"""
        
        # Verify Google ID token
        user_info = await self.google_oauth.verify_id_token(google_request.id_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        # Check if user exists
        result = await db.execute(select(User).where(User.email == user_info["email"]))
        user = result.scalar_one_or_none()
        
        if user:
            # User exists, log them in
            action = UserAction.LOGIN
        else:
            # Create new user
            user = User(
                name=user_info["name"],
                email=user_info["email"],
                password=None,  # No password for OAuth users
                role=UserRole.SIGNED_UP,
                status=UserStatus.ACTIVE,
                email_verified=user_info.get("email_verified", True)
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            action = UserAction.SIGNUP
        
        # Create tokens
        access_token = SecurityService.create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        refresh_token = SecurityService.create_refresh_token()
        refresh_token_hash = SecurityService.hash_token(refresh_token)
        
        # Store refresh token
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            device_id=SecurityService.generate_device_id(),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        )
        
        db.add(db_refresh_token)
        
        # Log the action
        user_log = UserLog(
            user_id=user.id,
            action=action,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details="Google OAuth"
        )
        
        db.add(user_log)
        await db.commit()
        
        # Set cookies
        self._set_auth_cookies(response, access_token, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user).dict()
        )

    async def refresh_token(
        self,
        request: Request,
        response: Response,
        db: AsyncSession
    ) -> TokenResponse:
        """Refresh access token using refresh token"""
        
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        
        # Hash the token to find it in database
        refresh_token_hash = SecurityService.hash_token(refresh_token)
        
        # Find refresh token in database
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == refresh_token_hash)
        )
        db_refresh_token = result.scalar_one_or_none()
        
        if not db_refresh_token or not db_refresh_token.is_active():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        result = await db.execute(select(User).where(User.id == db_refresh_token.user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Invalidate old refresh token
        db_refresh_token.is_valid = False
        
        # Create new tokens
        access_token = SecurityService.create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        new_refresh_token = SecurityService.create_refresh_token()
        new_refresh_token_hash = SecurityService.hash_token(new_refresh_token)
        
        # Store new refresh token
        new_db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_token_hash,
            device_id=db_refresh_token.device_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        )
        
        db.add(new_db_refresh_token)
        await db.commit()
        
        # Set new cookies
        self._set_auth_cookies(response, access_token, new_refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user).dict()
        )

    async def logout(
        self,
        request: Request,
        response: Response,
        current_user: User,
        db: AsyncSession
    ) -> LogoutResponse:
        """Logout user and invalidate refresh token"""
        
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            refresh_token_hash = SecurityService.hash_token(refresh_token)
            
            # Invalidate refresh token
            result = await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == refresh_token_hash)
            )
            db_refresh_token = result.scalar_one_or_none()
            if db_refresh_token:
                db_refresh_token.is_valid = False
        
        # Log the logout
        user_log = UserLog(
            user_id=current_user.id,
            action=UserAction.LOGOUT,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        db.add(user_log)
        await db.commit()
        
        # Clear cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return LogoutResponse()

    def _set_auth_cookies(self, response: Response, access_token: str, refresh_token: str):
        """Set authentication cookies"""
        
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.access_token_expire_minutes * 60,
            httponly=True,
            secure=not settings.debug,
            samesite="none" if not settings.debug else "lax"
        )
        
        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
            httponly=True,
            secure=not settings.debug,
            samesite="none" if not settings.debug else "lax"
        )