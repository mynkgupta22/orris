from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    id_token: str


class GoogleAuthURL(BaseModel):
    authorization_url: str
    state: str


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"