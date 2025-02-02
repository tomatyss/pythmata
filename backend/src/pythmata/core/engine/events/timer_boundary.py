from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from pythmata.core.engine.events.timer import TimerEvent, TimerCancelled
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

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
        interrupting: bool = True
    ):
        super().__init__(event_id, timer_def, state_manager)
        self.activity_id = activity_id
        self.interrupting = interrupting
        self._activity_completed = {}  # Track completion by instance ID

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
                    data=token.data
                )

            # Handle interrupting vs non-interrupting behavior
            if self.interrupting:
                # Remove token from activity
                await self.state_manager.remove_token(
                    instance_id=token.instance_id,
                    node_id=self.activity_id
                )
                # Cancel any other boundary events
                await self._cancel_other_boundary_events(token.instance_id)

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
            "interrupting": self.interrupting
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

    async def on_activity_completed(self, instance_id: str):
        """Handle activity completion."""
        self._activity_completed[instance_id] = True
        await self.cancel(instance_id)

    async def _cancel_other_boundary_events(self, instance_id: str):
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
                    await self.state_manager.delete_timer_state(instance_id, timer_id)

    async def _cleanup(self, instance_id: str):
        """Clean up timer and boundary event state."""
        await super()._cleanup(instance_id)
        self._activity_completed.pop(instance_id, None)

    @classmethod
    async def restore(
        cls,
        event_id: str,
        state: Dict[str, Any],
        state_manager: StateManager
    ) -> "TimerBoundaryEvent":
        """Restore timer boundary event from saved state."""
        timer = cls(
            event_id=event_id,
            timer_def=state["timer_definition"],
            state_manager=state_manager,
            activity_id=state["activity_id"],
            interrupting=state["interrupting"]
        )
        timer._state = state
        return timer
