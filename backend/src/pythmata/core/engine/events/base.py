from abc import ABC, abstractmethod
from pythmata.core.engine.token import Token

class Event(ABC):
    """Base class for all BPMN events"""
    def __init__(self, event_id: str):
        self.id = event_id
        
    @abstractmethod
    async def execute(self, token: Token) -> Token:
        """
        Execute the event behavior.
        
        Args:
            token: Process token containing execution context
            
        Returns:
            Updated token with execution results
        """
        pass
