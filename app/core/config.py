"""
KCapTrack — Application Settings & Environment Configuration.

All settings are loaded from environment variables with sensible defaults.
Use a `.env` file in the project root for local development.
"""

from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    # ── Application ─────────────────────────────────────────────────────
    APP_NAME: str = "KCapTrack"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kcaptrack"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/kcaptrack"

    # ── Security ────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-please"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # ── YOLO / CV ───────────────────────────────────────────────────────
    YOLO_WEIGHTS_PATH: str = "models/yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.40
    UPLOAD_DIR: str = "uploads"

    # ── Google Gemini Vision (free tier) ────────────────────────────────
    # Get your free API key at: https://aistudio.google.com/app/apikey
    # 1,500 requests/day free, no credit card required
    GEMINI_API_KEY: Optional[str] = None

    # ── USDA FoodData Central (optional) ────────────────────────────────
    USDA_API_KEY: Optional[str] = None
    USDA_BASE_URL: str = "https://api.nal.usda.gov/fdc/v1"

    # ── Paths ───────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
