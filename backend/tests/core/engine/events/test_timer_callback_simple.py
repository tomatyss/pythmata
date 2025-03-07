"""Simplified test for timer callback function."""

from unittest.mock import MagicMock, patch

import pytest

from pythmata.core.engine.events.timer_scheduler import timer_callback


@patch("pythmata.core.engine.events.timer_scheduler.asyncio")
def test_timer_callback_simple(mock_asyncio):
    """Simplified test for timer callback that focuses only on event loop creation."""
    # Setup
    mock_loop = MagicMock()
    mock_asyncio.new_event_loop.return_value = mock_loop

    # Execute
    timer_callback("timer1", "def1", "node1", "duration", "PT1H")

    # Assert event loop creation and management
    mock_asyncio.new_event_loop.assert_called_once()

    # Check that set_event_loop was called twice:
    # First with the new loop, then with None at the end
    assert (
        mock_asyncio.set_event_loop.call_count == 2
    ), "set_event_loop should be called twice"
