"""Tests for error handling decorator in process execution."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from pythmata.core.engine.executor import handle_execution_error
from pythmata.core.engine.token import Token


@pytest.fixture
def mock_instance_manager():
    """Create a mock instance manager."""
    return MagicMock(handle_error=AsyncMock())


@pytest.fixture
def test_instance(mock_instance_manager):
    """Create test instance with mock instance manager."""
    class TestClass:
        """Test class for decorator testing."""
        @handle_execution_error
        async def successful_method(self, token: Token):
            """Test method that succeeds."""
            return "success"

        @handle_execution_error
        async def failing_method(self, token: Token, node_id: str = None):
            """Test method that raises an exception."""
            raise ValueError("Test error")

    instance = TestClass()
    instance.instance_manager = mock_instance_manager
    return instance


@pytest.fixture
def mock_token():
    """Create a mock token."""
    token = MagicMock()
    token.instance_id = "test-instance"
    return token


async def test_error_handler_preserves_successful_execution(test_instance, mock_token):
    """Test that decorator doesn't interfere with successful execution."""
    result = await test_instance.successful_method(mock_token)
    assert result == "success"
    # Verify error handler was not called
    test_instance.instance_manager.handle_error.assert_not_called()


async def test_error_handler_decorator_captures_exceptions(test_instance, mock_token):
    """Test that decorator properly catches and handles exceptions."""
    node_id = "test-node"
    
    with pytest.raises(ValueError) as exc_info:
        await test_instance.failing_method(mock_token, node_id)
    
    assert str(exc_info.value) == "Test error"
    
    # Verify error was properly handled
    test_instance.instance_manager.handle_error.assert_called_once_with(
        mock_token.instance_id, 
        exc_info.value,
        node_id
    )


async def test_error_handler_without_node_id(test_instance, mock_token):
    """Test error handling when no node_id is provided."""
    with pytest.raises(ValueError) as exc_info:
        await test_instance.failing_method(mock_token)
    
    assert str(exc_info.value) == "Test error"
    
    # Verify error was handled without node_id
    test_instance.instance_manager.handle_error.assert_called_once_with(
        mock_token.instance_id,
        exc_info.value,
        None
    )
