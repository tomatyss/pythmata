from typing import Any, Dict

from pythmata.core.engine.events.base import Event
from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager


class SignalEvent(Event):
    """
    Implementation of BPMN Signal Event.
    Handles broadcast signal communication between process instances.
    """

    def __init__(self, event_id: str, signal_name: str, state_manager: StateManager):
        super().__init__(event_id)
        self.signal_name = signal_name
        self.state_manager = state_manager

    def _validate_signal_payload(self, signal: Any) -> Dict:
        """
        Validate the signal payload format.

        Args:
            signal: The received signal data

        Returns:
            The validated payload dictionary

        Raises:
            ValueError: If the signal payload format is invalid
        """
        if not isinstance(signal, dict):
            raise ValueError(
                "Invalid signal payload format: payload must be a dictionary"
            )

        if "payload" not in signal:
            raise ValueError("Invalid signal payload format: missing 'payload' key")

        if signal["payload"] is None:
            raise ValueError("Invalid signal payload format: payload cannot be None")

        return signal["payload"]

    async def execute(self, token: Token) -> Token:
        """
        Execute the signal event by subscribing to a signal and waiting for it.
        Updates the token with the received signal payload.

        Args:
            token: The current process token

        Returns:
            Updated token with signal payload data

        Raises:
            ValueError: If the signal payload format is invalid
        """
        try:
            # Register signal subscription
            await self.state_manager.set_signal_subscription(
                self.signal_name, token.instance_id, token.node_id
            )

            # Wait for signal
            signal = await self.state_manager.wait_for_signal(
                self.signal_name, token.instance_id, token.node_id
            )

            # Validate and extract payload
            payload = self._validate_signal_payload(signal)

            # Update token with signal payload
            token.data["signal_payload"] = payload

            return token

        finally:
            # Ensure subscription is cleaned up in all cases
            await self.state_manager.remove_signal_subscription(
                self.signal_name, token.instance_id, token.node_id
            )
