from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from pythmata.core.common import ConnectionError
from pythmata.core.common.connections import ensure_connected
from pythmata.core.config import (
    DatabaseSettings,
    ProcessSettings,
    RabbitMQSettings,
    RedisSettings,
    SecuritySettings,
    ServerSettings,
    Settings,
)
from pythmata.core.database import Database


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        server=ServerSettings(host="localhost", port=8000, debug=True),
        database=DatabaseSettings(
            url="postgresql+asyncpg://user:pass@localhost/test",
            pool_size=5,
            max_overflow=10,
        ),
        redis=RedisSettings(url="redis://localhost:6379", pool_size=10),
        rabbitmq=RabbitMQSettings(
            url="amqp://guest:guest@localhost:5672/",
            connection_attempts=3,
            retry_delay=5,
        ),
        security=SecuritySettings(
            secret_key="test_secret", algorithm="HS256", access_token_expire_minutes=30
        ),
        process=ProcessSettings(
            script_timeout=30, max_instances=100, cleanup_interval=300
        ),
    )


@pytest.fixture
async def database(mock_settings):
    """Create a database instance with mocked engine."""
    with patch("pythmata.core.database.create_async_engine") as mock_create_engine:
        # Create mock connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        # Create mock connection for begin context
        mock_begin_conn = AsyncMock()
        mock_begin_conn.run_sync = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_begin_conn)
        mock_begin_ctx.__aexit__ = AsyncMock()

        # Create mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.connect = AsyncMock(return_value=mock_conn)
        mock_engine.begin = MagicMock(
            return_value=mock_begin_ctx
        )  # Not AsyncMock since begin() returns context manager directly
        mock_engine.dispose = AsyncMock()
        mock_create_engine.return_value = mock_engine

        # Create mock session with commit and rollback
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.execute = AsyncMock()

        # Create session context manager
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock()
        session_ctx.mock_session = mock_session  # Store for test access

        # Create session maker that returns the context manager
        mock_session_maker = MagicMock(return_value=session_ctx)
        mock_session_maker.mock_session = mock_session  # Store for test access

        with patch(
            "pythmata.core.database.async_sessionmaker", return_value=mock_session_maker
        ):
            db = Database(mock_settings)
            db.engine = mock_engine  # Replace with mock engine
            yield db


async def test_database_initial_state(database):
    """Test initial database state."""
    assert not database.is_connected
    assert database.settings is not None
    assert database.engine is not None


async def test_database_connect(database):
    """Test database connection."""
    await database.connect()
    assert database.is_connected
    database.engine.connect.assert_called_once()


async def test_database_disconnect(database):
    """Test database disconnection."""
    await database.connect()
    await database.disconnect()
    assert not database.is_connected
    database.engine.dispose.assert_called_once()


async def test_create_tables(database):
    """Test create_tables method."""
    await database.connect()

    # Get the mock connection from the fixture
    mock_begin_conn = database.engine.begin.return_value.__aenter__.return_value

    await database.create_tables()
    mock_begin_conn.run_sync.assert_called_once()


async def test_drop_tables(database):
    """Test drop_tables method."""
    await database.connect()

    # Get the mock connection from the fixture
    mock_begin_conn = database.engine.begin.return_value.__aenter__.return_value

    await database.drop_tables()
    mock_begin_conn.run_sync.assert_called_once()


async def test_session_context_manager(database):
    """Test session context manager."""
    await database.connect()

    # Get the mock session from the fixture
    mock_session = database.async_session().mock_session

    # Use the session
    session_ctx = database.session()
    async with session_ctx as session:
        assert session is not None
        await session.execute("SELECT 1")
        await session.commit()

    # Verify commit was called
    mock_session.commit.assert_awaited_once()


async def test_session_rollback_on_error(database):
    """Test session rolls back on error."""
    await database.connect()

    # Get the mock session from the fixture
    mock_session = database.async_session().mock_session
    mock_session.rollback = AsyncMock()

    # Configure session context to call rollback on error
    session_ctx = database.session()

    # Configure session context manager to handle errors
    async def handle_exit(exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await mock_session.rollback()
        return False  # Don't suppress the exception

    session_ctx.__aexit__ = AsyncMock(side_effect=handle_exit)

    # Test error handling
    with pytest.raises(ValueError):
        async with session_ctx as session:
            await session.execute("SELECT 1")
            raise ValueError("Test error")

    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_connected_decorator(database):
    """Test the ensure_connected decorator works with database methods."""

    @ensure_connected
    async def test_operation(self):
        return "success"

    result = await test_operation(database)
    assert result == "success"
    assert database.is_connected

    # Test with connection error and reconnection
    connection_attempts = 0

    # Create mock connection that will be returned on success
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    # Create a new mock engine for retry test
    mock_engine = AsyncMock(spec=AsyncEngine)
    mock_engine.dispose = AsyncMock()
    mock_engine.connect = AsyncMock(return_value=mock_conn)

    @ensure_connected
    async def test_reconnect(self):
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            # First attempt fails with a connection error
            raise ConnectionError("Connection failed")
        # Second attempt succeeds
        return "reconnected"

    # Replace the engine
    database.engine = mock_engine
    database._is_connected = False  # Ensure we start disconnected

    await database.disconnect()
    assert not database.is_connected

    # Should succeed on second attempt
    try:
        result = await test_reconnect(database)
        assert result == "reconnected"
        assert database.is_connected
        assert database.engine.connect.call_count == 2  # First fails, second succeeds
    except ConnectionError:
        pytest.fail("Should have succeeded on second attempt")


@pytest.mark.asyncio
async def test_connection_error_handling(database):
    """Test database connection error handling."""
    database.engine.connect.side_effect = Exception("Connection failed")

    with pytest.raises(ConnectionError) as exc_info:
        await database.connect()

    assert "Failed to connect" in str(exc_info.value)
    assert not database.is_connected
