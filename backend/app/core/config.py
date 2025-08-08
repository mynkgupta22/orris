from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "EVIDEV Chatbot API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql://postgres:root@localhost:5432/orris1"
    
    # JWT
    jwt_secret_key: str = "default-secret-key"
    jwt_refresh_secret_key: str = "default-refresh-secret-key"
    jwt_algorithm: str = "HS512"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    
    # Google Drive
    google_drive_folder_id: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    def get_allowed_origins(self) -> List[str]:
        if self.allowed_origins:
            return [origin.strip() for origin in self.allowed_origins.split(",")]
        return ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()