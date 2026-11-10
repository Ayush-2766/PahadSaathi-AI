"""Environment-backed application settings."""
from dataclasses import dataclass
import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("PAHADSAATHI_APP_NAME", "PahadSaathi AI")
    environment: str = os.getenv("PAHADSAATHI_ENVIRONMENT", "development")
    database_url: str = os.getenv("PAHADSAATHI_DATABASE_URL", "sqlite:///./pahadsaathi.db")
    debug: bool = _as_bool(os.getenv("PAHADSAATHI_DEBUG", "false"))


settings = Settings()

