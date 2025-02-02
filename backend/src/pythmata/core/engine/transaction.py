from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, UTC


class TransactionStatus(str, Enum):
    """Possible states of a transaction."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Transaction:
    """
    Represents a BPMN transaction boundary and manages transaction state.
    
    A transaction is a unit of work that follows ACID properties:
    - Atomicity: All work within transaction completes or none of it does
    - Consistency: Transaction maintains process consistency
    - Isolation: Changes are isolated until transaction completes
    - Durability: Once committed, changes are permanent
    """
    id: str
    instance_id: str
    status: TransactionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    parent_transaction_id: Optional[str] = None
    compensation_handlers: Dict[str, Any] = None
    
    @classmethod
    def start(cls, transaction_id: str, instance_id: str) -> "Transaction":
        """
        Start a new transaction.
        
        Args:
            transaction_id: ID of the transaction element
            instance_id: ID of the process instance
            
        Returns:
            New Transaction instance in ACTIVE state
        """
        return cls(
            id=transaction_id,
            instance_id=instance_id,
            status=TransactionStatus.ACTIVE,
            start_time=datetime.now(UTC),
            compensation_handlers={}
        )
    
    def complete(self) -> None:
        """Mark transaction as successfully completed."""
        self.status = TransactionStatus.COMPLETED
        self.end_time = datetime.now(UTC)
    
    def fail(self) -> None:
        """Mark transaction as failed, triggering compensation."""
        self.status = TransactionStatus.FAILED
        self.end_time = datetime.now(UTC)
    
    def cancel(self) -> None:
        """Mark transaction as cancelled."""
        self.status = TransactionStatus.CANCELLED
        self.end_time = datetime.now(UTC)
    
    def register_compensation_handler(self, activity_id: str, handler: Any) -> None:
        """
        Register a compensation handler for an activity.
        
        Args:
            activity_id: ID of the activity that may need compensation
            handler: Compensation handler function/object
        """
        self.compensation_handlers[activity_id] = handler
    
    def is_active(self) -> bool:
        """Check if transaction is still active."""
        return self.status == TransactionStatus.ACTIVE
    
    def requires_compensation(self) -> bool:
        """Check if transaction requires compensation."""
        return self.status in [TransactionStatus.FAILED, TransactionStatus.CANCELLED]
