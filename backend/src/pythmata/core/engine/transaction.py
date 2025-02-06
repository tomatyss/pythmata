from enum import Enum
from typing import Dict, List, Optional, Set

from .events.compensation import CompensationScope
from .token import Token, TokenState


class TransactionStatus(Enum):
    """Represents the possible states of a transaction"""

    ACTIVE = "active"
    COMMITTED = "committed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class Transaction(CompensationScope):
    """Represents a transaction boundary that can contain compensatable activities"""

    @classmethod
    def start(cls, transaction_id: str, instance_id: str) -> "Transaction":
        """
        Start a new transaction.

        Args:
            transaction_id: ID of the transaction element
            instance_id: ID of the process instance

        Returns:
            New Transaction instance
        """
        return cls(transaction_id, instance_id)

    def __init__(
        self,
        transaction_id: str,
        instance_id: str,
        parent_scope: Optional["CompensationScope"] = None,
    ):
        """
        Initialize transaction

        Args:
            transaction_id: Unique identifier for this transaction
            instance_id: ID of the process instance this transaction belongs to
            parent_scope: Optional parent scope for nested transactions
        """
        super().__init__(transaction_id, parent_scope)
        self.instance_id = instance_id
        self.completed_activities: Set[str] = set()
        self.status = TransactionStatus.ACTIVE

    def complete(self) -> None:
        """Complete the transaction successfully"""
        self.status = TransactionStatus.COMMITTED

    def cancel(self) -> None:
        """Cancel the transaction and trigger compensation"""
        self.status = TransactionStatus.COMPENSATING

    def mark_completed(self, activity_id: str) -> None:
        """Mark an activity as completed within this transaction"""
        self.completed_activities.add(activity_id)

    def is_completed(self, activity_id: str) -> bool:
        """Check if an activity has been completed"""
        return activity_id in self.completed_activities


class TransactionContext:
    """Manages the execution context and state of a transaction"""

    def __init__(self, transaction: Transaction):
        """
        Initialize transaction context

        Args:
            scope: The transaction scope this context manages
        """
        self.scope = transaction
        self.state = TransactionStatus.ACTIVE
        self._participants: Dict[str, Token] = (
            {}
        )  # Maps activity IDs to their completion tokens

    async def record_completion(self, token: Token) -> None:
        """
        Record the completion of an activity in this transaction

        Args:
            token: Token representing the completed activity
        """
        activity_id = token.node_id
        self._participants[activity_id] = token
        self.scope.mark_completed(activity_id)

    def has_participant(self, activity_id: str) -> bool:
        """Check if an activity has participated in this transaction"""
        return activity_id in self._participants

    def get_participants(self) -> List[str]:
        """Get list of participating activity IDs"""
        return list(self._participants.keys())

    def requires_compensation(self) -> bool:
        """Check if transaction requires compensation"""
        return self.state in [TransactionStatus.COMPENSATING, TransactionStatus.FAILED]

    async def commit(self) -> Token:
        """
        Commit the transaction

        Returns:
            Token: Token representing the transaction completion
        """
        if not self._participants:
            raise ValueError("Cannot commit empty transaction")

        self.state = TransactionStatus.COMMITTED

        # Use the last participant's token as base for result
        last_token = next(reversed(self._participants.values()))
        return Token(
            instance_id=last_token.instance_id,
            node_id=last_token.node_id,
            state=TokenState.ACTIVE,
            data=last_token.data,
        )

    async def rollback(self) -> Token:
        """
        Rollback the transaction by triggering compensation

        Returns:
            Token: Compensation token for the first activity to compensate
        """
        if not self._participants:
            raise ValueError("Cannot rollback empty transaction")

        self.state = TransactionStatus.COMPENSATING

        # Get first activity to compensate (LIFO order)
        activity_id, token = next(reversed(self._participants.items()))

        # Get compensation handler for the activity
        handler = self.scope.get_handler_for_activity(activity_id)
        if not handler:
            raise ValueError(
                f"No compensation handler found for activity {activity_id}"
            )

        # Create compensation token targeting the handler
        compensation_data = {
            "compensate_scope_id": self.scope.scope_id,
            "compensated_activity_id": activity_id,
            "original_activity_data": token.data,
            "compensation_scope_id": self.scope.scope_id,  # Add scope ID for nested transactions
        }

        # If this is a nested transaction, include parent scope information
        if self.scope.parent_scope:
            compensation_data["parent_scope_id"] = self.scope.parent_scope.scope_id

        return Token(
            instance_id=token.instance_id,
            node_id=handler.handler_id,  # Use handler's ID instead of activity ID
            state=TokenState.COMPENSATION,
            data=compensation_data,
        )
