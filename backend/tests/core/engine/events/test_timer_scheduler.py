"""Tests for timer scheduler module."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pythmata.core.engine.events.timer_parser import TimerDefinition
from pythmata.core.engine.events.timer_scheduler import TimerScheduler, timer_callback


@pytest.fixture
def state_manager():
    """Create a mock state manager."""
    state_manager = AsyncMock()
    state_manager.redis = AsyncMock()
    state_manager.redis.connection_pool.connection_kwargs = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    }
    return state_manager


@pytest.fixture
def event_bus():
    """Create a mock event bus."""
    return AsyncMock()


@pytest.fixture
def scheduler(state_manager, event_bus):
    """Create a timer scheduler instance with mocked dependencies."""
    scheduler = TimerScheduler(state_manager, event_bus)
    scheduler._create_scheduler = AsyncMock(
        return_value=AsyncMock(spec=AsyncIOScheduler)
    )
    return scheduler


class TestTimerScheduler:
    """Test suite for timer scheduler."""

    @pytest.mark.asyncio
    async def test_start(self, scheduler):
        """Test starting the scheduler."""
        # Setup
        scheduler._schedule_recovery_timers = AsyncMock()
        scheduler._scan_for_timer_start_events = AsyncMock()

        # Execute
        await scheduler.start()

        # Assert
        assert scheduler._running is True
        assert scheduler._scheduler.start.called
        assert scheduler._schedule_recovery_timers.called
        assert scheduler._scan_for_timer_start_events.called
        assert scheduler._scan_task is not None

    @pytest.mark.asyncio
    async def test_stop(self, scheduler):
        """Test stopping the scheduler."""
        # Setup
        scheduler._running = True
        scheduler._scan_task = asyncio.create_task(asyncio.sleep(0.1))
        scheduler._scheduler = AsyncMock()

        # Execute
        await scheduler.stop()

        # Assert
        assert scheduler._running is False
        assert scheduler._scheduler.shutdown.called

    @pytest.mark.asyncio
    async def test_recover_from_crash(self, scheduler, state_manager):
        """Test recovering timer state after a crash."""
        # Setup
        state_manager.redis.keys.return_value = ["pythmata:timer:123:metadata"]
        state_manager.redis.get.return_value = json.dumps(
            {
                "definition_id": "def1",
                "node_id": "node1",
                "timer_def": "PT1H",
                "timer_type": "duration",
            }
        )
        scheduler._schedule_recovery_timers = AsyncMock()

        # Execute
        await scheduler.recover_from_crash()

        # Assert
        assert len(scheduler._recovery_metadata) == 1
        assert scheduler._recovery_metadata[0]["timer_id"] == "pythmata:timer:123"
        assert scheduler._recovery_metadata[0]["definition_id"] == "def1"
        assert scheduler._recovery_metadata[0]["node_id"] == "node1"
        assert scheduler._recovery_metadata[0]["timer_def"] == "PT1H"

    @pytest.mark.asyncio
    async def test_schedule_recovery_timers(self, scheduler):
        """Test scheduling timers from recovery metadata."""
        # Setup
        scheduler._recovery_metadata = [
            {
                "timer_id": "timer1",
                "definition_id": "def1",
                "node_id": "node1",
                "timer_def": "PT1H",
            }
        ]
        scheduler._schedule_timer = AsyncMock()

        # Execute
        await scheduler._schedule_recovery_timers()

        # Assert
        scheduler._schedule_timer.assert_called_once_with(
            "timer1", "def1", "node1", "PT1H"
        )
        assert scheduler._recovery_metadata == []

    @pytest.mark.asyncio
    async def test_schedule_timer(self, scheduler, state_manager):
        """Test scheduling a timer."""
        # Setup
        timer_id = "timer1"
        definition_id = "def1"
        node_id = "node1"
        timer_def = "PT1H"

        # Create a more complete mock of TimerDefinition
        timer_definition = MagicMock(spec=TimerDefinition)
        timer_definition.timer_type = "duration"
        timer_definition.trigger = MagicMock()
        
        # Ensure the Redis mock won't raise exceptions
        state_manager.redis.set = AsyncMock()
        
        with patch(
            "pythmata.core.engine.events.timer_scheduler.parse_timer_definition",
            return_value=timer_definition,
        ):
            # Ensure scheduler is properly initialized
            scheduler._scheduler = MagicMock()
            scheduler._scheduler.get_job.return_value = None

            # Execute
            await scheduler._schedule_timer(timer_id, definition_id, node_id, timer_def)

            # Debug assertions
            assert scheduler._scheduler is not None, "Scheduler is None"
            
            # Assert
            assert timer_id in scheduler._scheduled_timer_ids
            state_manager.redis.set.assert_called_once()
            
            # Check if add_job was called at all
            assert scheduler._scheduler.add_job.called, "add_job was not called"
            
            # Check the actual call arguments
            actual_args = scheduler._scheduler.add_job.call_args
            expected_args = call(
                timer_callback,
                trigger=timer_definition.trigger,
                id=timer_id,
                replace_existing=True,
                kwargs={
                    "timer_id": timer_id,
                    "definition_id": definition_id,
                    "node_id": node_id,
                    "timer_type": timer_definition.timer_type,
                    "timer_def": timer_def,
                },
            )
            
            # Compare the actual and expected arguments
            assert actual_args == expected_args, f"Expected: {expected_args}, Got: {actual_args}"

    @pytest.mark.asyncio
    async def test_remove_timer(self, scheduler, state_manager):
        """Test removing a timer."""
        # Setup
        timer_id = "timer1"
        scheduler._scheduled_timer_ids.add(timer_id)
        scheduler._scheduler = MagicMock()

        # Execute
        await scheduler._remove_timer(timer_id)

        # Assert
        assert timer_id not in scheduler._scheduled_timer_ids
        scheduler._scheduler.remove_job.assert_called_once_with(timer_id)
        state_manager.redis.delete.assert_called_once_with(f"{timer_id}:metadata")


# Import the module directly to ensure correct patching
import pythmata.core.engine.events.timer_scheduler

@patch("pythmata.core.config.Settings")
@patch("pythmata.core.state.StateManager")
@patch("pythmata.core.events.EventBus")
@patch("pythmata.core.database.get_db")
@patch.object(pythmata.core.engine.events.timer_scheduler, 'asyncio')  # Patch the module directly
def test_timer_callback(
    mock_asyncio, mock_get_db, mock_event_bus, mock_state_manager, mock_settings
):
    """Test the timer callback function."""
    # Setup mocks
    mock_loop = MagicMock()
    mock_asyncio.new_event_loop.return_value = mock_loop
    mock_asyncio.set_event_loop = MagicMock()

    mock_state_manager_instance = MagicMock()
    mock_event_bus_instance = MagicMock()
    mock_db_instance = MagicMock()

    mock_state_manager.return_value = mock_state_manager_instance
    mock_event_bus.return_value = mock_event_bus_instance
    mock_get_db.return_value = mock_db_instance

    # Mock UUID generation
    test_uuid = uuid.uuid4()
    with patch("uuid.uuid4", return_value=test_uuid):
        try:
            # Execute
            timer_callback("timer1", "def1", "node1", "duration", "PT1H")
        except Exception as e:
            pytest.fail(f"Exception raised during timer_callback: {e}")

        # Assert
        mock_asyncio.new_event_loop.assert_called_once()
        
        # Check that set_event_loop was called twice:
        # First with the new loop, then with None at the end
        assert mock_asyncio.set_event_loop.call_count == 2, "set_event_loop should be called twice"
        assert mock_asyncio.set_event_loop.call_args_list[0] == call(mock_loop), "First call should set the new loop"
        assert mock_asyncio.set_event_loop.call_args_list[1] == call(None), "Second call should set None"

        # Check that run_until_complete was called for connect, publish, and disconnect
        assert mock_loop.run_until_complete.call_count == 3, f"Expected 3 calls to run_until_complete, got {mock_loop.run_until_complete.call_count}"

        # Check loop was closed
        mock_loop.close.assert_called_once()
