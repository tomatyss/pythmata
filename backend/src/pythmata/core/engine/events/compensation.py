from typing import Dict, Any, Optional, List
from .base import Event
from .boundary import BoundaryEvent
from ..token import Token, TokenState

class CompensationScope:
    """Represents a compensation scope that can contain compensation handlers"""
    
    def __init__(self, scope_id: str, parent_scope: Optional['CompensationScope'] = None):
        """
        Initialize compensation scope
        
        Args:
            scope_id: Unique identifier for this scope
            parent_scope: Optional parent scope for nested compensation
        """
        self.scope_id = scope_id
        self.parent_scope = parent_scope
        self.handlers: List[CompensationBoundaryEvent] = []
        self._ordered_handlers: Dict[str, int] = {}  # Maps handler IDs to execution order
        
    def add_handler(self, handler: 'CompensationBoundaryEvent') -> None:
        """Add a compensation handler to this scope"""
        self.handlers.append(handler)
        if hasattr(handler, 'execution_order'):
            self._ordered_handlers[handler.event_id] = handler.execution_order
        
    def get_handler_for_activity(self, activity_id: str) -> Optional['CompensationBoundaryEvent']:
        """Get compensation handler for specific activity"""
        for handler in self.handlers:
            if handler.attached_to_id == activity_id:
                return handler
        return None
        
    def get_ordered_handlers(self) -> List['CompensationBoundaryEvent']:
        """Get handlers in execution order"""
        if not self._ordered_handlers:
            return self.handlers  # Return in registration order if no explicit ordering
            
        # Sort handlers by execution order
        ordered = sorted(
            self.handlers,
            key=lambda h: self._ordered_handlers.get(h.event_id, float('inf'))
        )
        return ordered
        
    def is_ancestor_of(self, scope: 'CompensationScope') -> bool:
        """Check if this scope is an ancestor of the given scope"""
        current = scope
        while current.parent_scope is not None:
            if current.parent_scope == self:
                return True
            current = current.parent_scope
        return False

class CompensationEventDefinition:
    """Definition for compensation events"""
    
    def __init__(self, activity_ref: Optional[str] = None, scope: Optional[CompensationScope] = None):
        """
        Initialize compensation event definition
        
        Args:
            activity_ref: Optional reference to specific activity to compensate.
                         If None, compensates the current scope.
            scope: Optional scope for this compensation event
        """
        self.activity_ref = activity_ref
        self.scope = scope

class CompensationBoundaryEvent(BoundaryEvent):
    """Boundary event that handles compensation"""
    
    def __init__(self, event_id: str, attached_to_id: str, handler_id: str, 
                 scope: Optional[CompensationScope] = None, execution_order: Optional[int] = None):
        """
        Initialize compensation boundary event.
        
        Args:
            event_id: Unique identifier for the event
            attached_to_id: ID of the activity this event is attached to
            handler_id: ID of the compensation handler activity
            scope: Optional scope this event belongs to
            execution_order: Optional order for parallel compensation execution
        """
        super().__init__(event_id, attached_to_id)
        self.event_id = event_id  # Store event_id for compensation ordering
        self.handler_id = handler_id
        self.is_interrupting = False  # Compensation events are non-interrupting
        self.scope = scope
        if execution_order is not None:
            self.execution_order = execution_order
        if scope:
            scope.add_handler(self)
        
    def can_handle_compensation(self, token: Token) -> bool:
        """
        Check if this boundary event can handle the given compensation token.
        
        Args:
            token: Token containing compensation information
            
        Returns:
            bool: True if this event can handle the compensation, False otherwise
        """
        if token.state != TokenState.COMPENSATION:
            return False
            
        # Check if compensation is targeting a specific scope
        target_scope_id = token.data.get('compensate_scope_id')
        if target_scope_id and self.scope:
            if target_scope_id != self.scope.scope_id:
                return False
                
        # Check if compensation is targeting a specific activity
        target_activity_id = token.data.get('compensate_activity_id')
        if target_activity_id and target_activity_id != self.attached_to_id:
            return False
            
        return True
        
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
                'compensation_scope_id': self.scope.scope_id if self.scope else None,
                'original_activity_data': token.data.get('activity_data', {})
            }
        )
        
        return compensation_token

class CompensationActivity(Event):
    """Activity that performs compensation logic"""
    
    def __init__(self, event_id: str, compensate_activity_id: Optional[str] = None, scope: Optional[CompensationScope] = None):
        """
        Initialize compensation activity.
        
        Args:
            event_id: Unique identifier for the event
            compensate_activity_id: Optional ID of specific activity to compensate.
                                  If None, compensates the current scope.
            scope: Optional scope this activity belongs to
        """
        super().__init__(event_id)
        self.compensate_activity_id = compensate_activity_id
        self.scope = scope
        
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
        if self.compensate_activity_id:
            token.data['compensate_activity_id'] = self.compensate_activity_id
        if self.scope:
            token.data['compensate_scope_id'] = self.scope.scope_id
        
        return token
