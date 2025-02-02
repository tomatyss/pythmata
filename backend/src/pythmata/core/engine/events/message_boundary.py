from typing import Optional

from pythmata.core.engine.events.boundary import BoundaryEvent
from pythmata.core.engine.token import Token, TokenState
from pythmata.core.state import StateManager

class MessageBoundaryEvent(BoundaryEvent):
    """Implementation of BPMN message boundary events"""
    
    def __init__(
        self,
        event_id: str,
        attached_to_id: str,
        message_name: str,
        state_manager: StateManager,
        correlation_key: Optional[str] = None,
        is_interrupting: bool = True,
        timeout: Optional[int] = None
    ):
        """
        Initialize message boundary event.
        
        Args:
            event_id: Unique identifier for the event
            attached_to_id: ID of the activity this event is attached to
            message_name: Name of the message to listen for
            state_manager: State manager for handling message subscriptions
            correlation_key: Optional key for message correlation
            is_interrupting: Whether the event interrupts the attached activity
            timeout: Optional timeout in seconds for message reception
        """
        super().__init__(event_id, attached_to_id)
        self.message_name = message_name
        self.state_manager = state_manager
        self.correlation_key = correlation_key
        self.is_interrupting = is_interrupting
        self.timeout = timeout

    async def execute(self, token: Token) -> Token:
        """
        Execute message boundary event behavior.
        
        Args:
            token: Process token from the attached activity
            
        Returns:
            Updated token with execution results
            
        Raises:
            ValueError: If correlation key is specified but not found in token data
        """
        # Get correlation value if key is specified
        correlation_value = None
        if self.correlation_key:
            correlation_value = token.data.get(self.correlation_key)
            if correlation_value is None:
                raise ValueError(f"Correlation key '{self.correlation_key}' not found in token data")

        try:
            # Register message subscription
            await self.state_manager.set_message_subscription(
                self.message_name,
                token.instance_id,
                token.node_id,
                correlation_value=correlation_value
            )
            
            # Wait for message to arrive
            message = await self.state_manager.wait_for_message(
                self.message_name,
                token.instance_id,
                token.node_id,
                correlation_value=correlation_value
            )
            
            # Create new token for the boundary event path
            result_token = Token(
                instance_id=token.instance_id,
                node_id=self.id,
                state=TokenState.ACTIVE,
                data=token.data.copy()  # Preserve original task data
            )
            
            # Add message payload to token data
            result_token.data["message_payload"] = message["payload"]
            
            # If interrupting, update original token state
            if self.is_interrupting:
                token.state = TokenState.COMPLETED
                
            return result_token
                
        finally:
            # Ensure subscription is cleaned up in all cases
            await self.state_manager.remove_message_subscription(
                self.message_name,
                token.instance_id,
                token.node_id
            )
