"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Postal Code Genesis Platform"
    app_version: str = "1.0.0"
    debug: bool = True

    # Full DATABASE_URL (takes priority if set)
    database_url: str = ""

    # Individual DB parts (used when DATABASE_URL not set, e.g. on Render)
    db_host: str = ""
    db_port: str = "5432"
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "postal_genesis"

    # Google Maps
    google_maps_api_key: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def _build_url(self, driver: str) -> str:
        """Build a connection URL from parts or convert an existing one."""
        url = self.database_url

        if not url and self.db_host:
            url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )

        if not url:
            url = "postgresql://postgres:postgres@localhost:5432/postal_genesis"

        # Ensure correct driver
        if driver == "asyncpg":
            if url.startswith("postgresql+psycopg2://"):
                url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif driver == "psycopg2":
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg2" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

        return url

    def get_async_url(self) -> str:
        return self._build_url("asyncpg")

    def get_sync_url(self) -> str:
        return self._build_url("psycopg2")


settings = Settings()
