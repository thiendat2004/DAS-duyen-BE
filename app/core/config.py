from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "DAS Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/das_db"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/das_db"

    SECRET_KEY: str = "das-super-secret-key-2026-betterus-system"
    REFRESH_SECRET_KEY: str = "das-refresh-super-secret-key-2026-betterus-system"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MAX_LOGIN_ATTEMPTS: int = 5
    # API Keys & AI Config
    GEMINI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "auto"  # Lựa chọn: "auto", "gemini", "llama"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://frettiest-ariella-unnationally.ngrok-free.dev",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
