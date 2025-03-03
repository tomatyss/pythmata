"""Tests for lifecycle utility functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythmata.core.utils.lifecycle import lifespan


@pytest.mark.asyncio
async def test_lifespan():
    """Test application lifespan (startup and shutdown)."""
    # Setup mocks
    mock_event_bus = AsyncMock()
    mock_state_manager = AsyncMock()
    mock_state_manager.get_token_positions = AsyncMock(return_value=None)
    mock_settings = MagicMock()
    mock_db = AsyncMock()
    mock_timer_scheduler = AsyncMock()
    mock_app = AsyncMock()
    mock_app.state = MagicMock()

    with (
        patch("pythmata.core.utils.lifecycle.EventBus", return_value=mock_event_bus),
        patch(
            "pythmata.core.utils.lifecycle.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.lifecycle.Settings", new=MagicMock(return_value=mock_settings)),
        patch("pythmata.core.utils.lifecycle.get_db", return_value=mock_db),
        patch("pythmata.core.utils.lifecycle.init_db"),
        patch(
            "pythmata.core.utils.lifecycle.initialize_timer_scheduler",
            return_value=mock_timer_scheduler,
        ),
        patch("pythmata.core.utils.lifecycle.discover_and_load_plugins"),
        patch("pythmata.core.utils.lifecycle.register_event_handlers") as mock_register_handlers,
        patch("pythmata.core.utils.lifecycle.get_service_task_registry") as mock_registry,
    ):
        # Configure mock registry to return some tasks
        mock_registry.return_value.list_tasks.return_value = [
            {"name": "http"},
            {"name": "logger"},
        ]

        # Call the lifespan function directly
        async with lifespan(mock_app):
            # Verify startup
            assert mock_event_bus.connect.called
            assert mock_state_manager.connect.called
            assert mock_db.connect.called
            assert mock_register_handlers.called

        # Verify shutdown after lifespan context exits
        assert mock_event_bus.disconnect.called
        assert mock_state_manager.disconnect.called
        assert mock_db.disconnect.called
        assert mock_timer_scheduler.stop.called


@pytest.mark.asyncio
async def test_lifespan_error_handling():
    """Test error handling during application shutdown."""
    # Setup mocks
    mock_event_bus = AsyncMock()
    mock_state_manager = AsyncMock()
    mock_settings = MagicMock()
    mock_db = AsyncMock()
    mock_timer_scheduler = AsyncMock()
    mock_app = AsyncMock()
    mock_app.state = MagicMock()

    # Configure mock to raise error during disconnect
    db_error = Exception("Database disconnect error")
    mock_db.disconnect.side_effect = db_error

    with (
        patch("pythmata.core.utils.lifecycle.EventBus", return_value=mock_event_bus),
        patch(
            "pythmata.core.utils.lifecycle.StateManager",
            return_value=mock_state_manager,
        ),
        patch("pythmata.core.utils.lifecycle.Settings", new=MagicMock(return_value=mock_settings)),
        patch("pythmata.core.utils.lifecycle.get_db", return_value=mock_db),
        patch("pythmata.core.utils.lifecycle.init_db"),
        patch(
            "pythmata.core.utils.lifecycle.initialize_timer_scheduler",
            return_value=mock_timer_scheduler,
        ),
        patch("pythmata.core.utils.lifecycle.discover_and_load_plugins"),
        patch("pythmata.core.utils.lifecycle.register_event_handlers"),
        patch("pythmata.core.utils.lifecycle.get_service_task_registry") as mock_registry,
    ):
        # Configure mock registry to return some tasks
        mock_registry.return_value.list_tasks.return_value = [
            {"name": "http"},
            {"name": "logger"},
        ]

        # Call the lifespan function directly
        async with lifespan(mock_app):
            # Verify startup succeeded
            assert mock_event_bus.connect.called
            assert mock_state_manager.connect.called
            assert mock_db.connect.called

        # The lifespan function catches exceptions during shutdown, so we can't
        # use pytest.raises. Instead, we verify that the disconnect method was called
        # and that the other services were still disconnected.
        assert mock_db.disconnect.called
        assert mock_event_bus.disconnect.called
        assert mock_state_manager.disconnect.called
        assert mock_timer_scheduler.stop.called
