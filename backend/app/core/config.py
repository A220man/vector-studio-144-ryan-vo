from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "vector-studio"
    secret_key: str = Field(default="dev-secret-change-in-production-32-chars-min", min_length=32)
    debug: bool = True
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_redirect_uri: Optional[str] = None

    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()