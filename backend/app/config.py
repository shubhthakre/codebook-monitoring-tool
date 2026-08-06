from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alert_enabled: bool = False
    alert_to: str = ""
    alert_from: str = "monitoring@localhost"
    alert_on_recovery: bool = True
    alert_cooldown_seconds: int = Field(default=300, ge=0)

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # Optional path to Oracle Instant Client (required for DB 11g / thick mode)
    oracle_client_lib_dir: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
