from enum import Enum


class TokenState(str, Enum):
    """Token execution states."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"  # Added for timer cancellation
    COMPENSATION = "COMPENSATION"  # Added for compensation handling
    WAITING = "WAITING"  # Added for call activities
