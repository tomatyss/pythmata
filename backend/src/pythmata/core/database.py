"""Database connection and session management."""

from typing import AsyncContextManager, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pythmata.core.common.connections import ConnectionManager, ensure_connected
from pythmata.core.config import Settings
from pythmata.models.process import Base
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


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
        self._connection_attempts = 0
        self._max_connection_attempts = 3
        self._retry_delay = 1.0  # seconds

        try:
            logger.info("Creating database engine...")
            # Create engine
            self.engine = create_async_engine(
                str(settings.database.url),
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                echo=settings.server.debug,
                pool_pre_ping=True,  # Enable connection health checks
            )

            logger.info("Creating session maker...")
            # Create session maker
            self.async_session = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def _do_connect(self) -> None:
        """Establish database connection.

        This method is called by the parent ConnectionManager's connect() method.
        Includes retry logic for handling temporary connection issues.
        """
        if not self.engine:
            logger.error("Database engine not initialized")
            raise RuntimeError("Database engine not initialized")

        while self._connection_attempts < self._max_connection_attempts:
            self._connection_attempts += 1
            try:
                logger.info(f"Attempting database connection (attempt {self._connection_attempts}/{self._max_connection_attempts})")
                
                # Test connection by creating a new connection
                conn = await self.engine.connect()
                try:
                    await conn.execute(text("SELECT 1"))
                    logger.info("Database connection test successful")
                    self._connection_attempts = 0  # Reset counter on success
                    return
                finally:
                    await conn.close()
                    
            except Exception as e:
                logger.error(f"Database connection attempt {self._connection_attempts} failed: {e}")
                if self._connection_attempts >= self._max_connection_attempts:
                    logger.error("Maximum connection attempts reached")
                    raise
                logger.info(f"Retrying in {self._retry_delay} seconds...")
                import asyncio
                await asyncio.sleep(self._retry_delay)

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

        async with self.engine.begin() as conn:
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

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped")

    async def close(self) -> None:
        """Close database connection.

        Alias for disconnect() to maintain compatibility with test fixtures.
        """
        await self.disconnect()

    def session(self) -> AsyncContextManager[AsyncSession]:
        """Get a database session.

        This context manager ensures proper session lifecycle management
        including commit/rollback handling.

        Usage:
            async with db.session() as session:
                result = await session.execute(...)

        Returns:
            AsyncContextManager yielding an AsyncSession
        """
        if not self.is_connected:
            logger.error("Attempted to get session but database is not connected")
            raise RuntimeError("Database not connected. Call connect() first")
        if not self.async_session:
            logger.error("Session maker not initialized")
            raise RuntimeError("Session maker not initialized")

        logger.debug("Creating new database session")
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
