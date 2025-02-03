from typing import Dict, Optional
from uuid import UUID, uuid4

from pythmata.core.types import TokenState

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
        token_id: Optional[UUID] = None,
        scope_id: Optional[str] = None,
        parent_instance_id: Optional[str] = None,
        parent_activity_id: Optional[str] = None,
    ):
        self.id = token_id or uuid4()
        self.instance_id = instance_id
        self.node_id = node_id
        self.state = state
        self.data = data or {}
        self.scope_id = scope_id
        self.parent_instance_id = parent_instance_id
        self.parent_activity_id = parent_activity_id

    def to_dict(self) -> Dict:
        """Convert token to dictionary for storage."""
        data = {
            "id": str(self.id),
            "instance_id": self.instance_id,
            "node_id": self.node_id,
            "state": self.state.value,
            "data": self.data,
            "scope_id": self.scope_id,
            "parent_instance_id": self.parent_instance_id,
            "parent_activity_id": self.parent_activity_id,
        }
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "Token":
        """Create token from dictionary representation."""
        return cls(
            instance_id=data["instance_id"],
            node_id=data["node_id"],
            state=TokenState(data["state"]),
            data=data.get("data", {}),
            token_id=UUID(data["id"]) if "id" in data else None,
            scope_id=data.get("scope_id"),
            parent_instance_id=data.get("parent_instance_id"),
            parent_activity_id=data.get("parent_activity_id"),
        )

    def copy(self, **kwargs) -> "Token":
        """Create a copy of this token with optional overrides."""
        data = self.to_dict()
        data.update(kwargs)
        if "id" in data:  # Ensure new copy gets new ID unless explicitly provided
            del data["id"]
        return Token.from_dict(data)
