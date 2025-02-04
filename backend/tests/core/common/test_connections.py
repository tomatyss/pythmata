from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

from pythmata.core.common.connections import (
    ConnectionError,
    ConnectionManager,
    ensure_connected,
)


class MockConnectionManager(ConnectionManager):
    """Mock implementation of ConnectionManager for testing."""

    def __init__(self):
        super().__init__()
        self.mock_connection: Optional[str] = None

    async def _do_connect(self) -> None:
        """Mock connection implementation."""
        self.mock_connection = "connected"

    async def _do_disconnect(self) -> None:
        """Mock disconnection implementation."""
        self.mock_connection = None


@pytest.fixture
def connection_manager():
    """Fixture providing a MockConnectionManager instance."""
    return MockConnectionManager()


async def test_initial_state(connection_manager):
    """Test initial connection state."""
    assert not connection_manager.is_connected
    assert connection_manager.mock_connection is None


async def test_successful_connection(connection_manager):
    """Test successful connection."""
    await connection_manager.connect()
    assert connection_manager.is_connected
    assert connection_manager.mock_connection == "connected"


async def test_successful_disconnection(connection_manager):
    """Test successful disconnection."""
    await connection_manager.connect()
    await connection_manager.disconnect()
    assert not connection_manager.is_connected
    assert connection_manager.mock_connection is None


async def test_double_connection(connection_manager):
    """Test connecting when already connected."""
    await connection_manager.connect()
    await connection_manager.connect()  # Should not raise or change state
    assert connection_manager.is_connected
    assert connection_manager.mock_connection == "connected"


async def test_disconnect_when_not_connected(connection_manager):
    """Test disconnecting when not connected."""
    await connection_manager.disconnect()  # Should not raise
    assert not connection_manager.is_connected


@pytest.mark.asyncio
async def test_connection_error_handling(connection_manager):
    """Test error handling during connection."""
    with patch.object(
        connection_manager, "_do_connect", side_effect=Exception("Connection failed")
    ):
        with pytest.raises(ConnectionError) as exc_info:
            await connection_manager.connect()
        assert "Failed to connect" in str(exc_info.value)
        assert not connection_manager.is_connected


@pytest.mark.asyncio
async def test_disconnection_error_handling(connection_manager):
    """Test error handling during disconnection."""
    await connection_manager.connect()
    with patch.object(
        connection_manager,
        "_do_disconnect",
        side_effect=Exception("Disconnection failed"),
    ):
        with pytest.raises(ConnectionError) as exc_info:
            await connection_manager.disconnect()
        assert "Failed to disconnect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_context_manager(connection_manager):
    """Test using connection manager as a context manager."""
    async with connection_manager:
        assert connection_manager.is_connected
        assert connection_manager.mock_connection == "connected"
    assert not connection_manager.is_connected
    assert connection_manager.mock_connection is None


@pytest.mark.asyncio
async def test_context_manager_with_error(connection_manager):
    """Test context manager handles errors properly."""
    with pytest.raises(ValueError):
        async with connection_manager:
            assert connection_manager.is_connected
            raise ValueError("Test error")
    assert not connection_manager.is_connected  # Should disconnect even if error occurs


@pytest.mark.asyncio
async def test_ensure_connected_decorator(connection_manager):
    """Test the ensure_connected decorator."""

    @ensure_connected
    async def test_function(self):
        return "success"

    # Should auto-connect before running
    result = await test_function(connection_manager)
    assert result == "success"
    assert connection_manager.is_connected

    # Should use existing connection
    result = await test_function(connection_manager)
    assert result == "success"
    assert connection_manager.is_connected


@pytest.mark.asyncio
async def test_ensure_connected_reconnection(connection_manager):
    """Test that ensure_connected attempts reconnection on connection errors."""
    connection_attempts = 0

    @ensure_connected
    async def test_function(self):
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            raise ConnectionError("Test connection error")
        return "success"

    # Should reconnect and succeed on second attempt
    result = await test_function(connection_manager)
    assert result == "success"
    assert connection_attempts == 2
    assert connection_manager.is_connected
