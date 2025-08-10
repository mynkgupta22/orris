from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars instead of raising
    )
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
    google_service_account_path: str = ""
    evidev_data_folder_id: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    
    # Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: str = "6333"
    qdrant_collection_name: str = "orris_rag"
    
    # Embeddings
    nomic_api_key: str = ""
    
    # Document Processing
    chunk_size: str = "800"
    chunk_overlap: str = "50"
    temp_dir: str = "/tmp"
    
    # Webhook Configuration
    webhook_base_url: str = ""
    google_webhook_token: str = ""
    gdrive_root_id: str = ""
    
    # CORS
    allowed_origins: str = "http://192.168.0.87:3000,http://localhost:8080,http://192.168.0.93:8001,http://localhost:8001"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60 
    
    def get_allowed_origins(self) -> List[str]:
        if self.allowed_origins:
            return [origin.strip() for origin in self.allowed_origins.split(",")]
        return ["http://192.168.0.87:3000", "http://localhost:8080"]
    
    # (Removed legacy inner Config to avoid conflict with model_config in Pydantic v2)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()