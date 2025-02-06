"""Database connection and session management."""
import logging
from typing import AsyncContextManager, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pythmata.core.common.connections import ConnectionManager, ensure_connected
from pythmata.core.config import Settings
from pythmata.models.process import Base

logger = logging.getLogger(__name__)


class Database(ConnectionManager):
    """Database connection and session management.

    This class manages the database connection lifecycle and provides
    session management utilities. It inherits from ConnectionManager
    to provide consistent connection handling across the application.
    """

    def __init__(self, settings: Settings):
        """Initialize database with settings.

        Args:
            settings: Application settings containing database configuration
        """
        super().__init__()
        self.settings = settings
        self.engine: Optional[AsyncEngine] = None
        self.async_session: Optional[async_sessionmaker[AsyncSession]] = None

        # Create engine
        self.engine = create_async_engine(
            str(settings.database.url),
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            echo=settings.server.debug,
        )

        # Create session maker
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _do_connect(self) -> None:
        """Establish database connection.

        This method is called by the parent ConnectionManager's connect() method.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        # Test connection by creating a new connection
        conn = await self.engine.connect()
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()

    async def _do_disconnect(self) -> None:
        """Close database connection.

        This method is called by the parent ConnectionManager's disconnect() method.
        """
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    @ensure_connected
    async def create_tables(self) -> None:
        """Create all database tables.

        This method is decorated with @ensure_connected to guarantee
        a valid connection before execution.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        begin_ctx = await self.engine.begin()
        async with begin_ctx as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

    @ensure_connected
    async def drop_tables(self) -> None:
        """Drop all database tables.

        This method is decorated with @ensure_connected to guarantee
        a valid connection before execution.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        begin_ctx = await self.engine.begin()
        async with begin_ctx as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped")

    @ensure_connected
    async def session(self) -> AsyncContextManager[AsyncSession]:
        """Get a database session.

        This context manager ensures proper session lifecycle management
        including commit/rollback handling.

        Usage:
            async with db.session() as session:
                result = await session.execute(...)

        Returns:
            AsyncContextManager yielding an AsyncSession
        """
        if not self.async_session:
            raise RuntimeError("Session maker not initialized")

        return self.async_session()


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the database instance.

    Returns:
        Database: The global database instance

    Raises:
        RuntimeError: If database is not initialized
    """
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def init_db(settings: Settings) -> None:
    """Initialize the database.

    Args:
        settings: Application settings containing database configuration
    """
    global _db
    _db = Database(settings)
