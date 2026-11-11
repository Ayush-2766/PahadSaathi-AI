"""Environment-backed application settings."""
from dataclasses import dataclass
import os


def _database_url() -> str:
    url = os.getenv("PAHADSAATHI_DATABASE_URL", "sqlite:///./pahadsaathi.db").strip()
    # Use the pure-Python PyMySQL driver for managed MySQL URLs on Render.
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    return url


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("PAHADSAATHI_APP_NAME", "PahadSaathi AI")
    environment: str = os.getenv("PAHADSAATHI_ENVIRONMENT", "development")
    database_url: str = _database_url()
    debug: bool = _as_bool(os.getenv("PAHADSAATHI_DEBUG", "false"))


settings = Settings()
