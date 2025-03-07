#!/usr/bin/env python3
"""Script to set up the test database."""

import asyncio
import sys

import asyncpg

from pythmata.core.testing.config import POSTGRES_MAIN_DB, POSTGRES_TEST_DB, get_db_url
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


async def check_db_exists(db_name: str) -> bool:
    """Check if database exists."""
    try:
        conn = await asyncpg.connect(
            get_db_url(database=POSTGRES_MAIN_DB, for_asyncpg=True)
        )
        result = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        await conn.close()
        return bool(result)
    except Exception as e:
        logger.error(f"Error checking database existence: {e}")
        return False


async def drop_test_database() -> None:
    """Drop test database if it exists."""
    try:
        conn = await asyncpg.connect(
            get_db_url(database=POSTGRES_MAIN_DB, for_asyncpg=True)
        )
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = $1
            AND pid <> pg_backend_pid()
            """,
            POSTGRES_TEST_DB,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{POSTGRES_TEST_DB}"')
        await conn.close()
        logger.info(f"Dropped database '{POSTGRES_TEST_DB}'")
    except Exception as e:
        logger.error(f"Error dropping test database: {e}")


async def create_test_database() -> None:
    """Create test database if it doesn't exist."""
    try:
        # First drop existing database to ensure clean state
        await drop_test_database()

        # Connect to default database to create test database
        conn = await asyncpg.connect(
            get_db_url(database=POSTGRES_MAIN_DB, for_asyncpg=True)
        )
        await conn.execute(f'CREATE DATABASE "{POSTGRES_TEST_DB}"')
        await conn.close()
        logger.info(f"Created database '{POSTGRES_TEST_DB}'")

    except Exception as e:
        logger.error(f"Error creating test database: {e}")
        raise


async def main():
    """Main function to set up test database."""
    try:
        await create_test_database()
        logger.info("Test database setup completed successfully")
    except Exception as e:
        logger.error(f"Test database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
