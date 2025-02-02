import re
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, Any
import json

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

class TimerCancelled(Exception):
    """Raised when a timer is cancelled."""
    pass

class TimerEvent(Event):
    """Implementation of BPMN timer events"""
    
    def __init__(self, event_id: str, timer_def: str, state_manager: StateManager):
        super().__init__(event_id)
        self.state_manager = state_manager
        self.timer_definition = timer_def
        self._parse_timer_definition(timer_def)
        self._active_tasks = {}

    def _parse_timer_definition(self, timer_def: str):
        """Parse ISO 8601 timer definition."""
        # Try parsing as duration (e.g., PT1H)
        if timer_def.startswith("PT"):
            self.timer_type = "duration"
            self.duration = self._parse_duration(timer_def)
            self.target_date = None
            self.interval = None
            self.repetitions = None
            return

        # Try parsing as cycle (e.g., R3/PT1H)
        if timer_def.startswith("R"):
            self.timer_type = "cycle"
            match = re.match(r"R(\d+)/PT(.+)$", timer_def)
            if not match:
                raise ValueError(f"Invalid cycle timer format: {timer_def}")
            self.repetitions = int(match.group(1))
            self.interval = self._parse_duration(f"PT{match.group(2)}")
            self.duration = None
            self.target_date = None
            return

        # Try parsing as date
        try:
            self.timer_type = "date"
            self.target_date = datetime.fromisoformat(timer_def)
            self.duration = None
            self.interval = None
            self.repetitions = None
            return
        except ValueError:
            pass

        raise ValueError(f"Invalid timer definition: {timer_def}")

    def _parse_duration(self, duration_str: str) -> timedelta:
        """Parse ISO 8601 duration string."""
        if not duration_str.startswith("PT"):
            raise ValueError(f"Invalid duration format: {duration_str}")

        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_str)
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}")

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    async def execute(self, token: Token) -> Token:
        """Execute timer behavior."""
        try:
            if self.timer_type == "duration":
                await self._execute_duration(token)
            elif self.timer_type == "date":
                await self._execute_date(token)
            elif self.timer_type == "cycle":
                await self._execute_cycle(token)

            return Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.COMPLETED,
                data=token.data
            )
        except TimerCancelled:
            return Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.CANCELLED,
                data=token.data
            )

    async def _execute_duration(self, token: Token):
        """Execute duration timer."""
        await self.start(token)
        try:
            await asyncio.sleep(self.duration.total_seconds())
        except asyncio.CancelledError:
            raise TimerCancelled()
        finally:
            await self._cleanup(token.instance_id)

    async def _execute_date(self, token: Token):
        """Execute date timer."""
        await self.start(token)
        now = datetime.now()
        if self.target_date > now:
            try:
                await asyncio.sleep((self.target_date - now).total_seconds())
            except asyncio.CancelledError:
                raise TimerCancelled()
        await self._cleanup(token.instance_id)

    async def _execute_cycle(self, token: Token):
        """Execute cycle timer."""
        await self.start(token)
        try:
            for _ in range(self.repetitions):
                await asyncio.sleep(self.interval.total_seconds())
        except asyncio.CancelledError:
            raise TimerCancelled()
        finally:
            await self._cleanup(token.instance_id)

    async def start(self, token: Token):
        """Start timer and save state."""
        state = {
            "timer_type": self.timer_type,
            "timer_definition": self.timer_definition,
            "start_time": datetime.now().isoformat(),
            "token_data": token.data
        }

        if self.timer_type == "duration":
            state["end_time"] = (
                datetime.now() + self.duration
            ).isoformat()
        elif self.timer_type == "date":
            state["end_time"] = self.target_date.isoformat()
        elif self.timer_type == "cycle":
            state["end_time"] = (
                datetime.now() + 
                self.interval * self.repetitions
            ).isoformat()

        await self.state_manager.save_timer_state(
            token.instance_id,
            self.id,
            state
        )

        # Store task for cancellation
        task = asyncio.current_task()
        if task:
            self._active_tasks[token.instance_id] = task

    async def cancel(self, instance_id: str):
        """Cancel timer execution."""
        task = self._active_tasks.get(instance_id)
        if task:
            task.cancel()
            del self._active_tasks[instance_id]
        await self._cleanup(instance_id)

    async def _cleanup(self, instance_id: str):
        """Clean up timer state."""
        await self.state_manager.delete_timer_state(instance_id, self.id)
        self._active_tasks.pop(instance_id, None)

    @property
    def remaining_time(self) -> Optional[timedelta]:
        """Get remaining time for timer."""
        if not hasattr(self, '_state'):
            return None
        
        end_time = datetime.fromisoformat(self._state["end_time"])
        return end_time - datetime.now()

    @classmethod
    async def restore(cls, event_id: str, state: Dict[str, Any], 
                     state_manager: StateManager) -> "TimerEvent":
        """Restore timer from saved state."""
        timer = cls(event_id, state["timer_definition"], state_manager)
        timer._state = state
        return timer
