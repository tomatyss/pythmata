from enum import Enum
from typing import Dict, Optional
from uuid import UUID, uuid4

class TokenState(str, Enum):
    """Token execution states."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class Token:
    """
    Represents a process execution token that moves through BPMN nodes.
    
    A token is created when a process instance starts and moves through the process
    nodes as the process executes. Tokens can be split at parallel gateways and
    merged at joining gateways.
    """
    
    def __init__(
        self,
        instance_id: str,
        node_id: str,
        state: TokenState = TokenState.ACTIVE,
        data: Optional[Dict] = None,
        token_id: Optional[UUID] = None
    ):
        self.id = token_id or uuid4()
        self.instance_id = instance_id
        self.node_id = node_id
        self.state = state
        self.data = data or {}

    def to_dict(self) -> Dict:
        """Convert token to dictionary for storage."""
        return {
            "id": str(self.id),
            "instance_id": self.instance_id,
            "node_id": self.node_id,
            "state": self.state.value,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Token":
        """Create token from dictionary representation."""
        return cls(
            instance_id=data["instance_id"],
            node_id=data["node_id"],
            state=TokenState(data["state"]),
            data=data.get("data", {}),
            token_id=UUID(data["id"]) if "id" in data else None
        )

    def copy(self, **kwargs) -> "Token":
        """Create a copy of this token with optional overrides."""
        data = self.to_dict()
        data.update(kwargs)
        if "id" in data:  # Ensure new copy gets new ID unless explicitly provided
            del data["id"]
        return Token.from_dict(data)
