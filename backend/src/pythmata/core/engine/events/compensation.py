from typing import Dict, Any, Optional
from .base import Event
from .boundary import BoundaryEvent
from ..token import Token, TokenState

class CompensationEventDefinition:
    """Definition for compensation events"""
    
    def __init__(self, activity_ref: Optional[str] = None):
        """
        Initialize compensation event definition
        
        Args:
            activity_ref: Optional reference to specific activity to compensate.
                         If None, compensates the current scope.
        """
        self.activity_ref = activity_ref

class CompensationBoundaryEvent(BoundaryEvent):
    """Boundary event that handles compensation"""
    
    def __init__(self, event_id: str, attached_to_id: str, handler_id: str):
        """
        Initialize compensation boundary event.
        
        Args:
            event_id: Unique identifier for the event
            attached_to_id: ID of the activity this event is attached to
            handler_id: ID of the compensation handler activity
        """
        super().__init__(event_id, attached_to_id)
        self.handler_id = handler_id
        self.is_interrupting = False  # Compensation events are non-interrupting
        
    def can_handle_compensation(self, token: Token) -> bool:
        """
        Check if this boundary event can handle the given compensation token.
        
        Args:
            token: Token containing compensation information
            
        Returns:
            bool: True if this event can handle the compensation, False otherwise
        """
        return (
            token.state == TokenState.COMPENSATION and 
            (token.data.get('compensate_activity_id') == self.attached_to_id or
             token.data.get('compensate_activity_id') is None)
        )
        
    async def execute(self, token: Token) -> Token:
        """
        Execute the compensation behavior.
        
        Args:
            token: Process token containing execution context
            
        Returns:
            Updated token with execution results
        """
        if not self.can_handle_compensation(token):
            return token
            
        # Create new token for compensation handler
        compensation_token = Token(
            instance_id=token.instance_id,  # Preserve the instance ID
            node_id=self.handler_id,
            state=TokenState.ACTIVE,
            data={
                **token.data,
                'compensated_activity_id': self.attached_to_id,
                'original_activity_data': token.data.get('activity_data', {})
            }
        )
        
        return compensation_token

class CompensationActivity(Event):
    """Activity that performs compensation logic"""
    
    def __init__(self, event_id: str, compensate_activity_id: Optional[str] = None):
        """
        Initialize compensation activity.
        
        Args:
            event_id: Unique identifier for the event
            compensate_activity_id: Optional ID of specific activity to compensate.
                                  If None, compensates the current scope.
        """
        super().__init__(event_id)
        self.compensate_activity_id = compensate_activity_id
        
    async def execute(self, token: Token) -> Token:
        """
        Execute the compensation activity.
        
        Args:
            token: Process token containing execution context
            
        Returns:
            Updated token with compensation state
        """
        # Set compensation state and target
        token.state = TokenState.COMPENSATION
        token.data['compensate_activity_id'] = self.compensate_activity_id
        
        return token
