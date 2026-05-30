"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional
import re


class Settings(BaseSettings):
    app_name: str = "Postal Code Genesis Platform"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database — Render provides DATABASE_URL in postgresql:// format
    # We convert to async format automatically
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postal_genesis"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/postal_genesis"

    # Google Maps
    google_maps_api_key: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_async_url(self) -> str:
        """Return async-compatible DATABASE_URL (postgresql+asyncpg://)."""
        url = self.database_url
        # Convert Render's postgresql:// to postgresql+asyncpg://
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def get_sync_url(self) -> str:
        """Return sync-compatible DATABASE_URL (postgresql+psycopg2://)."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
