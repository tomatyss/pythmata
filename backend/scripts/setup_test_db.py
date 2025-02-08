#!/usr/bin/env python3
"""Script to set up the test database."""

import asyncio
import logging
import os
from typing import Optional

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_DB_USER = "pythmata"
DEFAULT_DB_PASSWORD = "pythmata"
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = "5432"
DEFAULT_TEST_DB = "pythmata_test"
DEFAULT_MAIN_DB = "postgres"  # For initial connection to create test db

async def get_db_url(database: str = DEFAULT_MAIN_DB, for_asyncpg: bool = True) -> str:
    """Get database URL from environment variables or defaults."""
    user = os.getenv("POSTGRES_USER", DEFAULT_DB_USER)
    password = os.getenv("POSTGRES_PASSWORD", DEFAULT_DB_PASSWORD)
    host = os.getenv("POSTGRES_HOST", DEFAULT_DB_HOST)
    port = os.getenv("POSTGRES_PORT", DEFAULT_DB_PORT)
    
    if for_asyncpg:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

async def check_db_exists(db_name: str) -> bool:
    """Check if database exists."""
    try:
        conn = await asyncpg.connect(await get_db_url(for_asyncpg=True))
        result = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        await conn.close()
        return bool(result)
    except Exception as e:
        logger.error(f"Error checking database existence: {e}")
        raise

async def create_test_database() -> None:
    """Create test database if it doesn't exist."""
    db_name = os.getenv("POSTGRES_TEST_DB", DEFAULT_TEST_DB)
    
    try:
        exists = await check_db_exists(db_name)
        if exists:
            logger.info(f"Database '{db_name}' already exists")
            return

        # Connect to default database to create test database
        conn = await asyncpg.connect(await get_db_url(for_asyncpg=True))
        await conn.execute(f'CREATE DATABASE "{db_name}"')
        await conn.close()
        logger.info(f"Created database '{db_name}'")

    except Exception as e:
        logger.error(f"Error creating test database: {e}")
        raise

def run_migrations() -> None:
    """Run database migrations."""
    try:
        from alembic.config import Config
        from alembic import command
        import os

        # Get the absolute path to alembic.ini
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(current_dir, 'alembic.ini')
        
        # Create Alembic configuration
        alembic_cfg = Config(alembic_ini_path)
        
        # Set the SQLAlchemy URL in Alembic config
        test_db_url = f"postgresql://{os.getenv('POSTGRES_USER', DEFAULT_DB_USER)}:{os.getenv('POSTGRES_PASSWORD', DEFAULT_DB_PASSWORD)}@{os.getenv('POSTGRES_HOST', DEFAULT_DB_HOST)}:{os.getenv('POSTGRES_PORT', DEFAULT_DB_PORT)}/{os.getenv('POSTGRES_TEST_DB', DEFAULT_TEST_DB)}"
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
        
        # Run the migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

async def main():
    """Main function to set up test database."""
    try:
        await create_test_database()
        # Run migrations synchronously
        run_migrations()
        logger.info("Test database setup completed successfully")
    except Exception as e:
        logger.error(f"Test database setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
