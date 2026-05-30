"""Database setup with SQLAlchemy async + PostGIS."""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.get_async_url(),
    echo=settings.debug,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _add_column_if_missing(conn, table, column, col_type):
    """Add a column to a table if it doesn't already exist."""
    from sqlalchemy import text
    result = await conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
    """), {"table": table, "column": column})
    if result.scalar() is None:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        logger.info(f"Added column {table}.{column}")


async def init_db():
    """Initialize database, enable PostGIS, and auto-migrate missing columns."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.create_all)

            # Auto-migrate: add columns that exist in the model but not in the DB
            await _add_column_if_missing(conn, "countries", "capital_city", "VARCHAR(255)")
            await _add_column_if_missing(conn, "countries", "capital_lat", "FLOAT")
            await _add_column_if_missing(conn, "countries", "capital_lng", "FLOAT")

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database init failed (app will start anyway): {e}")
