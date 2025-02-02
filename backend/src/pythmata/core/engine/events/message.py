from asyncio import TimeoutError
from typing import Optional

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager


class MessageTimeoutError(Exception):
    """Raised when a message is not received within the specified timeout period."""

    pass


class MessageEvent(Event):
    """
    Implementation of BPMN Message Event.
    Handles message-based communication between process instances.
    """

    def __init__(
        self,
        event_id: str,
        message_name: str,
        state_manager: StateManager,
        correlation_key: str = None,
        timeout: Optional[int] = None,
    ):
        super().__init__(event_id)
        self.message_name = message_name
        self.state_manager = state_manager
        self.correlation_key = correlation_key
        self.timeout = timeout

    async def execute(self, token: Token) -> Token:
        """
        Execute the message event by subscribing to a message and waiting for it to arrive.
        Updates the token with the received message payload.

        Args:
            token: The current process token

        Returns:
            Updated token with message payload data

        Raises:
            ValueError: If correlation key is specified but not found in token data
            MessageTimeoutError: If message is not received within timeout period
        """
        # Get correlation value if key is specified
        correlation_value = None
        if self.correlation_key:
            correlation_value = token.data.get(self.correlation_key)
            if correlation_value is None:
                raise ValueError(
                    f"Correlation key '{self.correlation_key}' not found in token data"
                )

        try:
            # Register message subscription
            await self.state_manager.set_message_subscription(
                self.message_name,
                token.instance_id,
                token.node_id,
                correlation_value=correlation_value,
            )

            try:
                # Wait for message to arrive
                message = await self.state_manager.wait_for_message(
                    self.message_name,
                    token.instance_id,
                    token.node_id,
                    correlation_value=correlation_value,
                )

                # Update token with message payload
                token.data["message_payload"] = message["payload"]

                return token

            except TimeoutError:
                raise MessageTimeoutError(
                    f"Message '{self.message_name}' not received within {self.timeout} seconds"
                )

        finally:
            # Ensure subscription is cleaned up in all cases
            await self.state_manager.remove_message_subscription(
                self.message_name, token.instance_id, token.node_id
            )
