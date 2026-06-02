"""Application configuration using pydantic-settings."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = "Nigerian Real Estate Alert Platform"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://realestate_user:password@localhost:5432/realestate"
    )
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "realestate"
    postgres_user: str = "realestate_user"
    postgres_password: str = "password"

    # -------------------------------------------------------------------------
    # Redis & Celery
    # -------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------
    telegram_bot_token: str = Field(..., min_length=20)
    telegram_admin_chat_id: int | None = None

    # -------------------------------------------------------------------------
    # JWT / Admin Auth
    # -------------------------------------------------------------------------
    admin_username: str = "admin"
    admin_password: str = Field(..., min_length=8)
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # -------------------------------------------------------------------------
    # Scraper
    # -------------------------------------------------------------------------
    scraper_request_delay_seconds: float = 5.0
    scraper_max_retries: int = 3
    scraper_backoff_base: float = 2.0
    playwright_browser: str = "chromium"
    playwright_headless: bool = True
    disabled_scrapers: list[str] = Field(default_factory=list)

    @field_validator("disabled_scrapers", mode="before")
    @classmethod
    def parse_disabled_scrapers(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v or []

    @field_validator("database_url", mode="before")
    @classmethod
    def parse_database_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # -------------------------------------------------------------------------
    # Schedule
    # -------------------------------------------------------------------------
    scrape_interval_minutes: int = 15
    notification_retention_days: int = 90

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

    # -------------------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------------------
    metrics_enabled: bool = True

    # -------------------------------------------------------------------------
    # Computed helpers
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere."""
    return Settings()  # type: ignore[call-arg]
