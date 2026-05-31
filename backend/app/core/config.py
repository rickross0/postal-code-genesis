"""Application configuration using pydantic-settings."""
from urllib.parse import quote_plus

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
        """Build a connection URL from parts or convert an existing one.
        
        Priority: DB_* env vars > DATABASE_URL > fallback localhost.
        On Render, DB_HOST is set via fromService, so it always wins over
        any DATABASE_URL that might leak in from a .env file.
        """
        if self.db_host:
            # Individual DB_* parts take priority (e.g. on Render)
            encoded_password = quote_plus(self.db_password) if self.db_password else ""
            url = (
                f"postgresql://{self.db_user}:{encoded_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        elif self.database_url:
            url = self.database_url
        else:
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
