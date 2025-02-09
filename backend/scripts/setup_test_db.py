#!/usr/bin/env python3
"""Script to set up the test database."""

from pythmata.core.testing.config import (
    POSTGRES_MAIN_DB,
    POSTGRES_TEST_DB,
    get_db_url,
)
import asyncio
import logging
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_db_exists(db_name: str) -> bool:
    """Check if database exists."""
    try:
        conn = await asyncpg.connect(get_db_url(database=POSTGRES_MAIN_DB, for_asyncpg=True))
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
    db_name = POSTGRES_TEST_DB

    try:
        exists = await check_db_exists(db_name)
        if exists:
            logger.info(f"Database '{db_name}' already exists")
            return

        # Connect to default database to create test database
        conn = await asyncpg.connect(get_db_url(database=POSTGRES_MAIN_DB, for_asyncpg=True))
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
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(current_dir, 'alembic.ini')

        # Create Alembic configuration
        alembic_cfg = Config(alembic_ini_path)

        # Set the SQLAlchemy URL in Alembic config
        test_db_url = get_db_url(for_asyncpg=True)
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
