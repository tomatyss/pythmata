import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

__all__ = ["TimerEvent", "TimerBoundaryEvent", "TimerCancelled"]


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

    def _parse_timer_definition(self, timer_def: str) -> None:
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

    def _parse_duration(self, duration_str: str) -> timedelta | None:
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
                data=token.data,
            )
        except TimerCancelled:
            return Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.CANCELLED,
                data=token.data,
            )

    async def _execute_duration(self, token: Token) -> None:
        """Execute duration timer."""
        await self.start(token)
        try:
            await asyncio.sleep(self.duration.total_seconds())
        except asyncio.CancelledError:
            raise TimerCancelled()
        finally:
            await self._cleanup(token.instance_id)

    async def _execute_date(self, token: Token) -> None:
        """Execute date timer."""
        await self.start(token)
        now = datetime.now()
        if self.target_date > now:
            try:
                await asyncio.sleep((self.target_date - now).total_seconds())
            except asyncio.CancelledError:
                raise TimerCancelled()
        await self._cleanup(token.instance_id)

    async def _execute_cycle(self, token: Token) -> None:
        """Execute cycle timer."""
        await self.start(token)
        try:
            for _ in range(self.repetitions):
                await asyncio.sleep(self.interval.total_seconds())
        except asyncio.CancelledError:
            raise TimerCancelled()
        finally:
            await self._cleanup(token.instance_id)

    async def _get_task_key(self, instance_id: str) -> str:
        """Get Redis key for storing task info."""
        return f"process:{instance_id}:timer:{self.id}:task"

    async def _store_task(self, instance_id: str, task: asyncio.Task) -> None:
        """Store task info in Redis."""
        key = await self._get_task_key(instance_id)
        await self.state_manager.redis.set(key, str(id(task)))

    async def _get_task(self, instance_id: str) -> Optional[asyncio.Task]:
        """Get task from Redis."""
        key = await self._get_task_key(instance_id)
        task_id = await self.state_manager.redis.get(key)
        if task_id:
            # Find task by ID in all tasks
            for task in asyncio.all_tasks():
                if str(id(task)) == task_id:
                    return task
        return None

    async def _remove_task(self, instance_id: str) -> None:
        """Remove task info from Redis."""
        key = await self._get_task_key(instance_id)
        await self.state_manager.redis.delete(key)

    async def start(self, token: Token) -> None:
        """Start timer and save state."""
        state = {
            "timer_type": self.timer_type,
            "timer_definition": self.timer_definition,
            "start_time": datetime.now().isoformat(),
            "token_data": token.data,
        }

        if self.timer_type == "duration":
            state["end_time"] = (datetime.now() + self.duration).isoformat()
        elif self.timer_type == "date":
            state["end_time"] = self.target_date.isoformat()
        elif self.timer_type == "cycle":
            state["end_time"] = (
                datetime.now() + self.interval * self.repetitions
            ).isoformat()

        await self.state_manager.save_timer_state(token.instance_id, self.id, state)

        # Store task for cancellation
        task = asyncio.current_task()
        if task:
            await self._store_task(token.instance_id, task)

    async def cancel(self, instance_id: str) -> None:
        """Cancel timer execution."""
        task = await self._get_task(instance_id)
        if task:
            task.cancel()
            await self._remove_task(instance_id)
        await self._cleanup(instance_id)

    async def _cleanup(self, instance_id: str) -> None:
        """Clean up timer state."""
        await self.state_manager.delete_timer_state(instance_id, self.id)
        await self._remove_task(instance_id)

    @property
    def remaining_time(self) -> Optional[timedelta]:
        """Get remaining time for timer."""
        if not hasattr(self, "_state"):
            return None

        end_time = datetime.fromisoformat(self._state["end_time"])
        return end_time - datetime.now()

    @classmethod
    async def restore(
        cls, event_id: str, state: Dict[str, Any], state_manager: StateManager
    ) -> "TimerEvent":
        """Restore timer from saved state."""
        timer = cls(event_id, state["timer_definition"], state_manager)
        timer._state = state
        return timer


class TimerBoundaryEvent(TimerEvent):
    """
    Implementation of BPMN timer boundary events.

    Timer boundary events can be attached to activities and can be either:
    - Interrupting: Cancels the activity when timer triggers
    - Non-interrupting: Creates parallel execution path without cancelling activity
    """

    def __init__(
        self,
        event_id: str,
        timer_def: str,
        state_manager: StateManager,
        activity_id: str,
        interrupting: bool = True,
    ):
        super().__init__(event_id, timer_def, state_manager)
        self.activity_id = activity_id
        self.interrupting = interrupting
        self._activity_completed: Dict[
            str, bool
        ] = {}  # Track completion by instance ID

    async def execute(self, token: Token) -> Token:
        """Execute timer boundary event behavior."""
        try:
            # Store additional boundary event info
            await self.start(token)

            if self.timer_type == "duration":
                await self._execute_duration(token)
            elif self.timer_type == "date":
                await self._execute_date(token)
            elif self.timer_type == "cycle":
                await self._execute_cycle(token)

            # Check if activity completed during timer execution
            if self._activity_completed.get(token.instance_id, False):
                return Token(
                    instance_id=token.instance_id,
                    node_id=self.id,
                    state=TokenState.CANCELLED,
                    data=token.data,
                )

            # Handle interrupting vs non-interrupting behavior
            if self.interrupting:
                # Remove token from activity
                await self.state_manager.remove_token(
                    instance_id=token.instance_id, node_id=self.activity_id
                )
                # Cancel any other boundary events
                await self._cancel_other_boundary_events(token.instance_id)
            else:
                # For non-interrupting, add token back to activity
                await self.state_manager.add_token(
                    instance_id=token.instance_id,
                    node_id=self.activity_id,
                    data=token.data,
                )

            return Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.COMPLETED,
                data=token.data,
            )

        except TimerCancelled:
            return Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.CANCELLED,
                data=token.data,
            )
        finally:
            await self._cleanup(token.instance_id)

    async def start(self, token: Token):
        """Start timer and save boundary event state."""
        state = {
            "timer_type": self.timer_type,
            "timer_definition": self.timer_definition,
            "start_time": datetime.now().isoformat(),
            "token_data": token.data,
            "activity_id": self.activity_id,
            "interrupting": self.interrupting,
        }

        if self.timer_type == "duration":
            state["end_time"] = (datetime.now() + self.duration).isoformat()
        elif self.timer_type == "date":
            state["end_time"] = self.target_date.isoformat()
        elif self.timer_type == "cycle":
            state["end_time"] = (
                datetime.now() + self.interval * self.repetitions
            ).isoformat()

        await self.state_manager.save_timer_state(token.instance_id, self.id, state)

        # Store task for cancellation
        task = asyncio.current_task()
        if task:
            await self._store_task(token.instance_id, task)

    async def on_activity_completed(self, instance_id: str) -> None:
        """Handle activity completion."""
        self._activity_completed[instance_id] = True
        await self.cancel(instance_id)

    async def _cancel_other_boundary_events(self, instance_id: str) -> None:
        """Cancel other boundary events on the same activity."""
        # Get all timer states for this instance
        pattern = f"process:{instance_id}:timer:*"
        keys = await self.state_manager.redis.keys(pattern)

        for key in keys:
            timer_id = key.split(":")[-1]
            if timer_id != self.id:
                state = await self.state_manager.get_timer_state(instance_id, timer_id)
                if state and state.get("activity_id") == self.activity_id:
                    # Cancel other boundary event
                    other_timer = await TimerBoundaryEvent.restore(
                        timer_id, state, self.state_manager
                    )
                    # Get the task from Redis
                    task = await other_timer._get_task(instance_id)
                    if task:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    await other_timer._remove_task(instance_id)
                    await self.state_manager.delete_timer_state(instance_id, timer_id)

    async def _cleanup(self, instance_id: str) -> None:
        """Clean up timer and boundary event state."""
        await super()._cleanup(instance_id)
        self._activity_completed.pop(instance_id, None)

    @classmethod
    async def restore(
        cls, event_id: str, state: Dict[str, Any], state_manager: StateManager
    ) -> "TimerBoundaryEvent":
        """Restore timer boundary event from saved state."""
        timer = cls(
            event_id=event_id,
            timer_def=state["timer_definition"],
            state_manager=state_manager,
            activity_id=state["activity_id"],
            interrupting=state["interrupting"],
        )
        timer._state = state
        return timer
