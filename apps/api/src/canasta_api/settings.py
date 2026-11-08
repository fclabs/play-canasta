"""Env-backed settings and shared constants."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- constants (not from env) ---
SERVICE_NAME: Final[str] = "canasta-api"
API_PREFIX: Final[str] = "/api"
API_V1_PREFIX: Final[str] = "/api/v1"
DEFAULT_NAME: Final[str] = "player"
NAME_MIN_LENGTH: Final[int] = 1
NAME_MAX_LENGTH: Final[int] = 40
NAME_ALLOWED_PUNCTUATION: Final[frozenset[str]] = frozenset({" ", "'", "-", "_"})

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
AppEnv = Literal["local", "preview", "production"]


class Settings(BaseSettings):
    """Runtime settings; invalid values fail naming the env variable."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    log_level: LogLevel = Field(default="INFO", validation_alias="LOG_LEVEL")
    app_env: AppEnv = Field(default="local", validation_alias="APP_ENV")
    web_dist_dir: Path | None = Field(default=None, validation_alias="WEB_DIST_DIR")
