"""Configuration management"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://jang-yeonghwan@localhost/atlas_trading"
    )

    # Exchange API
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")

    # Backtesting
    default_initial_capital: float = float(os.getenv("DEFAULT_INITIAL_CAPITAL", "10000"))
    default_commission: float = float(os.getenv("DEFAULT_COMMISSION", "0.001"))

    class Config:
        env_file = ".env"


settings = Settings()
