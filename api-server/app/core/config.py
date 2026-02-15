"""API Server Configuration"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file using absolute path
ENV_PATH = Path("/Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform/.env")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    """API Server Settings"""

    # API
    api_title: str = "Atlas Trading API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # Database (shared with core-platform)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://jang-yeonghwan@localhost/atlas_trading"
    )

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server (default)
        "http://localhost:5174",  # Vite dev server (alt port)
        "http://localhost:5175",  # Vite dev server (alt port)
        "http://localhost:8080",
    ]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
