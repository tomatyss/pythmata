from typing import Dict, Optional

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token, TokenState


class EventSubprocess(Event):
    """
    Implementation of BPMN Event Subprocess.

    Event subprocesses are special activities that are triggered by events rather than
    being part of the normal flow. They can be either interrupting (cancelling the
    current scope) or non-interrupting (running in parallel).
    """

    def __init__(
        self,
        event_id: str,
        start_event_id: str,
        interrupting: bool = False,
        event_name: Optional[str] = None,
        event_type: Optional[str] = None,
    ):
        """
        Initialize event subprocess.

        Args:
            event_id: Unique identifier for this event subprocess
            start_event_id: ID of the start event within the subprocess
            interrupting: Whether this event subprocess interrupts its parent scope
            event_name: Optional name of the event that triggers this subprocess
            event_type: Optional type of the event (message, error, etc.)
        """
        super().__init__(event_id)
        self.start_event_id = start_event_id
        self.interrupting = interrupting
        self.event_name = event_name
        self.event_type = event_type

    async def execute(self, token: Token) -> Token:
        """
        Execute the event subprocess.

        This method is called when the triggering event occurs. It creates a new
        token in the event subprocess scope.

        Args:
            token: Token from the parent process

        Returns:
            New token positioned at the start event of the subprocess
        """
        # Create new token in subprocess scope
        subprocess_token = token.copy(
            node_id=self.start_event_id, scope_id=self.id, state=TokenState.ACTIVE
        )

        # If interrupting, cancel the parent scope token
        if self.interrupting:
            token.state = TokenState.CANCELLED

        return subprocess_token

    def matches_event(self, event_data: Dict) -> bool:
        """
        Check if this event subprocess matches the given event data.

        Args:
            event_data: Event data containing type and name

        Returns:
            True if this subprocess should be triggered by the event
        """
        if not self.event_type or not self.event_name:
            return False

        return (
            event_data.get("type") == self.event_type
            and event_data.get("name") == self.event_name
        )
