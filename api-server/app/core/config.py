"""API Server Configuration"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file using relative path from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / "core-platform"
ENV_PATH = Path(os.getenv("ENV_PATH", PROJECT_ROOT / ".env"))
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Core platform path for importing modules
CORE_PLATFORM_PATH = Path(os.getenv("CORE_PLATFORM_PATH", PROJECT_ROOT))


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

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")

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
