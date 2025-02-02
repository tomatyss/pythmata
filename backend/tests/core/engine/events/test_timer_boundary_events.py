import asyncio
from datetime import datetime, timedelta

import pytest

from pythmata.core.engine.events.timer import TimerBoundaryEvent, TimerCancelled
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager


@pytest.mark.asyncio
class TestTimerBoundaryEvents:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()

        yield

        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_interrupting_timer_boundary_event(self):
        """Test interrupting timer boundary event behavior"""
        timer = TimerBoundaryEvent(
            event_id="Timer_1",
            timer_def="PT2S",  # 2 second duration
            state_manager=self.state_manager,
            activity_id="Task_1",
            interrupting=True,
        )

        token = Token(
            instance_id="test-interrupt-1",
            node_id="Task_1",  # Token is in the activity
            data={"var1": "value1"},
        )

        # Start timer boundary event
        result = await timer.execute(token)

        # Verify token was moved to exception flow
        assert result.state == TokenState.COMPLETED
        assert result.instance_id == token.instance_id
        assert result.node_id == "Timer_1"  # Token moved to timer event
        assert result.data == {"var1": "value1"}  # Data preserved

        # Verify activity token was removed
        tokens = await self.state_manager.get_token_positions("test-interrupt-1")
        assert not any(t["node_id"] == "Task_1" for t in tokens)

    async def test_non_interrupting_timer_boundary_event(self):
        """Test non-interrupting timer boundary event behavior"""
        timer = TimerBoundaryEvent(
            event_id="Timer_1",
            timer_def="PT2S",  # 2 second duration
            state_manager=self.state_manager,
            activity_id="Task_1",
            interrupting=False,
        )

        token = Token(
            instance_id="test-non-interrupt-1",
            node_id="Task_1",  # Token is in the activity
            data={"var1": "value1"},
        )

        # Start timer boundary event
        result = await timer.execute(token)

        # Verify new token was created for exception flow
        assert result.state == TokenState.COMPLETED
        assert result.instance_id == token.instance_id
        assert result.node_id == "Timer_1"
        assert result.data == {"var1": "value1"}

        # Verify original activity token remains
        tokens = await self.state_manager.get_token_positions("test-non-interrupt-1")
        assert any(t["node_id"] == "Task_1" for t in tokens)

    async def test_timer_cancellation_on_activity_completion(self):
        """Test timer cancellation when activity completes"""
        timer = TimerBoundaryEvent(
            event_id="Timer_1",
            timer_def="PT1H",  # Long duration
            state_manager=self.state_manager,
            activity_id="Task_1",
            interrupting=True,
        )

        token = Token(instance_id="test-cancel-1", node_id="Task_1", data={})

        # Start timer in background
        execution = asyncio.create_task(timer.execute(token))

        # Simulate activity completion
        await asyncio.sleep(0.1)
        await timer.on_activity_completed(token.instance_id)

        result = await execution
        assert result.state == TokenState.CANCELLED

        # Verify timer state was cleaned up
        state = await self.state_manager.get_timer_state("test-cancel-1", "Timer_1")
        assert state is None

    async def test_multiple_timer_boundary_events(self):
        """Test multiple timer boundary events on same activity"""
        timer1 = TimerBoundaryEvent(
            event_id="Timer_1",
            timer_def="PT2S",
            state_manager=self.state_manager,
            activity_id="Task_1",
            interrupting=True,
        )

        timer2 = TimerBoundaryEvent(
            event_id="Timer_2",
            timer_def="PT3S",  # Changed from 1H to 3S for faster testing
            state_manager=self.state_manager,
            activity_id="Task_1",
            interrupting=False,
        )

        token = Token(
            instance_id="test-multiple-1", node_id="Task_1", data={"var1": "value1"}
        )

        # Start both timers
        timer1_execution = asyncio.create_task(timer1.execute(token))
        timer2_execution = asyncio.create_task(timer2.execute(token))

        # Wait for first timer to complete and cancel others
        await asyncio.sleep(2.1)  # Just after timer1's duration

        # First timer should be completed
        result1 = await timer1_execution
        assert result1.state == TokenState.COMPLETED

        # Second timer should be cancelled since timer1 interrupted the activity
        result2 = await timer2_execution
        assert result2.state == TokenState.CANCELLED

        # Verify all timer states were cleaned up
        state1 = await self.state_manager.get_timer_state("test-multiple-1", "Timer_1")
        state2 = await self.state_manager.get_timer_state("test-multiple-1", "Timer_2")
        assert state1 is None
        assert state2 is None
