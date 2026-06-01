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


async def _check_connection():
    """Test database connectivity and log clear diagnostics on failure."""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as e:
        error_msg = str(e)
        if "password authentication failed" in error_msg.lower() or "InvalidPassword" in error_msg:
            logger.error(
                "DATABASE AUTH FAILED: The DB_PASSWORD does not match POSTGRES_PASSWORD. "
                "In the Render dashboard, make sure the DB_PASSWORD env var on the web service "
                "matches the POSTGRES_PASSWORD env var on the postal-genesis-db service."
            )
        elif "connection refused" in error_msg.lower() or "could not connect" in error_msg.lower():
            logger.error(
                "DATABASE CONNECTION REFUSED: Cannot reach the database host. "
                "Verify DB_HOST and DB_PORT are set correctly."
            )
        else:
            logger.error(f"DATABASE CONNECTION ERROR: {e}")
        logger.error(f"  db_host={settings.db_host!r} db_port={settings.db_port!r} db_user={settings.db_user!r} db_name={settings.db_name!r}")
        logger.error(f"  db_password is {'SET' if settings.db_password else 'NOT SET (empty)'}")
        logger.error(f"  database_url is {'SET' if settings.database_url else 'NOT SET'}")
        return False


async def init_db():
    """Initialize database, enable PostGIS, create tables, and auto-migrate."""
    connected = await _check_connection()
    if not connected:
        logger.warning("Skipping database init — connection failed (see errors above)")
        return

    import asyncio
    for attempt in range(3):
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
                await _add_column_if_missing(conn, "countries", "locked", "BOOLEAN DEFAULT FALSE")
                await _add_column_if_missing(conn, "regions", "locked", "BOOLEAN DEFAULT FALSE")
                await _add_column_if_missing(conn, "districts", "locked", "BOOLEAN DEFAULT FALSE")
                await _add_column_if_missing(conn, "postal_zones", "locked", "BOOLEAN DEFAULT FALSE")
                await _add_column_if_missing(conn, "postal_zones", "color", "VARCHAR(7)")

            logger.info("Database initialized successfully")
            return
        except Exception as e:
            logger.error(f"Database init attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                logger.error("All database init attempts failed — tables may not exist")
