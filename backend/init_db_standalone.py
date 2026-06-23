#!/usr/bin/env python3
"""Standalone database initialization script.

Run this script to create all tables in the PostgreSQL database.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set the DATABASE_URL env var with the correct password
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', 'postgres123')
os.environ.setdefault('DB_NAME', 'postal_genesis')

from app.core.database import engine, Base
from app.models.database import Country, Region, District, PostalZone, Landmark, DrawingSnapshot
from sqlalchemy import text


async def init():
    print("Connecting to database...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)

    print("Enabling extensions...")
    async with engine.begin() as conn:
        # PostGIS was manually installed, just verify it works
        result = await conn.execute(text("SELECT PostGIS_Version()"))
        version = result.scalar()
        print(f"✓ PostGIS version: {version}")
        
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created")

        # Add missing columns (auto-migrate)
        migrations = [
            ("countries", "capital_city", "VARCHAR(255)"),
            ("countries", "capital_lat", "FLOAT"),
            ("countries", "capital_lng", "FLOAT"),
            ("countries", "locked", "BOOLEAN DEFAULT FALSE"),
            ("regions", "locked", "BOOLEAN DEFAULT FALSE"),
            ("districts", "locked", "BOOLEAN DEFAULT FALSE"),
            ("districts", "color", "VARCHAR(7)"),
            ("districts", "city_centers", "TEXT DEFAULT '[]'"),
            ("postal_zones", "locked", "BOOLEAN DEFAULT FALSE"),
            ("postal_zones", "color", "VARCHAR(7)"),
        ]
        for table, column, col_type in migrations:
            result = await conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            """), {"table": table, "column": column})
            if result.scalar() is None:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                ))
                print(f"  + Added {table}.{column}")

        # drawing_snapshots table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS drawing_snapshots (
                id SERIAL PRIMARY KEY,
                country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
                snapshot TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

    print("\n✓ Database initialization complete!")

    # Verify tables exist
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"\nExisting tables ({len(tables)}): {', '.join(tables)}")

        for expected in ['countries', 'regions', 'districts', 'postal_zones', 'landmarks', 'drawing_snapshots']:
            if expected in tables:
                print(f"  ✓ {expected}")
            else:
                print(f"  ✗ {expected} (MISSING!)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
