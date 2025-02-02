from abc import ABC

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token, TokenState


class BoundaryEvent(Event, ABC):
    """Base class for all BPMN boundary events"""

    def __init__(self, event_id: str, attached_to_id: str):
        """
        Initialize boundary event.

        Args:
            event_id: Unique identifier for the event
            attached_to_id: ID of the activity this event is attached to
        """
        super().__init__(event_id)
        self.attached_to_id = attached_to_id
        self.is_interrupting = True  # Default behavior for error events

    def can_handle_error(self, token: Token) -> bool:
        """
        Check if this boundary event can handle the given error token.

        Args:
            token: Token containing error information

        Returns:
            bool: True if this event can handle the error, False otherwise
        """
        return token.state == TokenState.ERROR and token.node_id == self.attached_to_id
