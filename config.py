"""Central application configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.absolute()
DB_PATH = BASE_DIR / "system.db"
LOGS_DIR = BASE_DIR / "logs"


class Settings(BaseSettings):
    dnevnik_token: Optional[str] = None
    dnevnik_base_url: str = "https://api.dnevnik.ru/v2"

    api_host: str = "127.0.0.1"
    api_port: int = 8080
    api_debug: bool = False

    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

MAIN_API_HOST = settings.api_host
MAIN_API_PORT = settings.api_port
MAIN_API_DEBUG = settings.api_debug
DNEVNIK_BASE_URL = settings.dnevnik_base_url
CORS_ORIGINS = settings.cors_origins
LOG_LEVEL = settings.log_level


def ensure_directories() -> None:
    """Create local folders used by the API."""
    LOGS_DIR.mkdir(exist_ok=True, parents=True)


def print_config() -> None:
    """Print a short runtime configuration summary."""
    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    print(f"Base dir: {BASE_DIR}")
    print(f"Database: {DB_PATH}")
    print(f"Logs: {LOGS_DIR}")
    print(f"API: http://{MAIN_API_HOST}:{MAIN_API_PORT}")
    print(f"Dnevnik base URL: {DNEVNIK_BASE_URL}")
    print("=" * 60 + "\n")
