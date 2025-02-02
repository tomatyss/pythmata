from typing import Optional

from pythmata.core.engine.events.boundary import BoundaryEvent
from pythmata.core.engine.token import Token, TokenState


class ErrorBoundaryEvent(BoundaryEvent):
    """Implementation of BPMN error boundary events"""

    def __init__(self, event_id: str, attached_to_id: str, error_code: str):
        """
        Initialize error boundary event.

        Args:
            event_id: Unique identifier for the event
            attached_to_id: ID of the activity this event is attached to
            error_code: Error code this event handles
        """
        super().__init__(event_id, attached_to_id)
        self.error_code = error_code

    def can_handle_error(self, token: Token) -> bool:
        """
        Check if this event can handle the given error token.

        Args:
            token: Token containing error information

        Returns:
            bool: True if this event can handle the error, False otherwise
        """
        if not super().can_handle_error(token):
            return False

        error_code = token.data.get("error", {}).get("code")
        return error_code == self.error_code

    async def execute(self, token: Token) -> Token:
        """
        Execute error boundary event behavior.

        Args:
            token: Process token containing error information

        Returns:
            Updated token with execution results
        """
        if not self.can_handle_error(token):
            # If we can't handle this error, propagate it unchanged
            return token

        # Create new token for the error path
        return Token(
            instance_id=token.instance_id,
            node_id=self.id,
            state=TokenState.ACTIVE,
            data=token.data,
        )
