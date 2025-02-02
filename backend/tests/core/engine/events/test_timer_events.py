import pytest
from datetime import datetime, timedelta
import asyncio
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.engine.events.timer import TimerEvent
from pythmata.core.state import StateManager

@pytest.mark.asyncio
class TestTimerEvents:
    @pytest.fixture(autouse=True)
    async def setup_test(self, test_settings):
        """Setup test environment and cleanup after."""
        self.state_manager = StateManager(test_settings)
        await self.state_manager.connect()
        
        yield
        
        # Cleanup after test
        await self.state_manager.redis.flushdb()
        await self.state_manager.disconnect()

    async def test_timer_event_creation(self):
        """Test timer event initialization with different time definitions"""
        # Test duration timer
        timer = TimerEvent("Timer_1", "PT1H", self.state_manager)
        assert timer.duration == timedelta(hours=1)
        assert timer.timer_type == "duration"
        
        # Test date timer
        date_str = "2025-02-01T15:00:00"
        timer = TimerEvent("Timer_2", date_str, self.state_manager)
        assert timer.target_date == datetime.fromisoformat(date_str)
        assert timer.timer_type == "date"
        
        # Test cycle timer
        timer = TimerEvent("Timer_3", "R3/PT1H", self.state_manager)
        assert timer.repetitions == 3
        assert timer.interval == timedelta(hours=1)
        assert timer.timer_type == "cycle"

    async def test_timer_duration_execution(self):
        """Test timer execution with duration"""
        # Use a short duration for testing
        timer = TimerEvent("Timer_1", "PT2S", self.state_manager)  # 2 second duration
        token = Token(
            instance_id="test-duration-1",
            node_id="Timer_1",
            data={}
        )
        
        start_time = datetime.now()
        result = await timer.execute(token)
        elapsed = datetime.now() - start_time
        
        assert elapsed >= timedelta(seconds=2)
        assert result.state == TokenState.COMPLETED
        assert result.instance_id == token.instance_id
        assert result.node_id == "Timer_1"

    async def test_timer_cancellation(self):
        """Test timer cancellation"""
        timer = TimerEvent("Timer_1", "PT1H", self.state_manager)
        token = Token(
            instance_id="test-cancel-1",
            node_id="Timer_1",
            data={}
        )
        
        # Start timer in background
        execution = asyncio.create_task(timer.execute(token))
        
        # Cancel after a short delay
        await asyncio.sleep(0.1)
        await timer.cancel("test-cancel-1")
        
        result = await execution
        assert result.state == TokenState.CANCELLED
        assert result.instance_id == token.instance_id
        assert result.node_id == "Timer_1"

    async def test_timer_state_persistence(self):
        """Test timer state is properly saved and restored"""
        timer = TimerEvent("Timer_1", "PT1H", self.state_manager)
        token = Token(
            instance_id="test-persist-1",
            node_id="Timer_1",
            data={"var1": "value1"}
        )
        
        # Start timer
        await timer.start(token)
        
        # Verify state is saved
        state = await self.state_manager.get_timer_state("test-persist-1", "Timer_1")
        assert state is not None
        assert state["end_time"] is not None
        assert state["timer_type"] == "duration"
        assert state["token_data"] == {"var1": "value1"}
        
        # Restore timer
        restored_timer = await TimerEvent.restore(
            "Timer_1",
            state,
            self.state_manager
        )
        assert restored_timer.id == "Timer_1"
        assert restored_timer.timer_type == "duration"
        assert restored_timer.remaining_time > timedelta(0)

    async def test_invalid_timer_definition(self):
        """Test handling of invalid timer definitions"""
        # Invalid duration format
        with pytest.raises(ValueError):
            TimerEvent("Timer_1", "1H", self.state_manager)
        
        # Invalid date format
        with pytest.raises(ValueError):
            TimerEvent("Timer_2", "2025-13-45", self.state_manager)
        
        # Invalid cycle format
        with pytest.raises(ValueError):
            TimerEvent("Timer_3", "R/1H", self.state_manager)

    async def test_cycle_timer_execution(self):
        """Test execution of repeating timer"""
        timer = TimerEvent("Timer_1", "R3/PT1S", self.state_manager)  # Repeat 3 times, 1 second each
        token = Token(
            instance_id="test-cycle-1",
            node_id="Timer_1",
            data={}
        )
        
        execution_times = []
        start_time = datetime.now()
        
        # Execute timer and collect completion times
        result = await timer.execute(token)
        end_time = datetime.now()
        
        # Verify execution time and repetitions
        total_elapsed = end_time - start_time
        assert total_elapsed >= timedelta(seconds=3)  # Should take at least 3 seconds
        assert result.state == TokenState.COMPLETED
        
        # Verify timer state was cleaned up
        state = await self.state_manager.get_timer_state("test-cycle-1", "Timer_1")
        assert state is None
