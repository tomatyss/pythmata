import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from fastapi import Request

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from pythmata.core.config import Settings
from pythmata.models.process import Base

logger = logging.getLogger(__name__)

class Database:
    """Database connection and session management."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_async_engine(
            str(settings.database.url),
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            echo=settings.server.debug
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session.
        
        Usage:
            async with db.session() as session:
                result = await session.execute(...)
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close database connection."""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def init_db(settings: Settings) -> None:
    """Initialize the database."""
    global _db
    _db = Database(settings)
