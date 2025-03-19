"""Core BPMN types and enums."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TokenState(str, Enum):
    """Token execution states."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    COMPENSATION = "COMPENSATION"
    WAITING = "WAITING"


class GatewayType(str, Enum):
    """Gateway types."""

    EXCLUSIVE = "exclusive"
    PARALLEL = "parallel"
    INCLUSIVE = "inclusive"


class EventType(str, Enum):
    """Event types."""

    START = "start"
    END = "end"
    INTERMEDIATE = "intermediate"
    BOUNDARY = "boundary"


@dataclass(frozen=True)
class FlowNode:
    """Base class for BPMN flow nodes."""

    id: str
    type: str
    name: Optional[str] = None
    incoming: List[str] = field(default_factory=list)
    outgoing: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Task(FlowNode):
    """Represents a BPMN task."""

    extensions: Dict[str, Any] = field(default_factory=dict)
    script: Optional[str] = None
    input_variables: Optional[Dict[str, str]] = field(default_factory=dict)
    output_variables: Optional[Dict[str, str]] = field(default_factory=dict)
    is_for_compensation: bool = False


@dataclass(frozen=True)
class Gateway(FlowNode):
    """Represents a BPMN gateway."""

    gateway_type: GatewayType = field(default=GatewayType.EXCLUSIVE)


@dataclass(frozen=True)
class Event(FlowNode):
    """Represents a BPMN event."""

    event_type: EventType = field(default=EventType.START)
    event_definition: Optional[str] = None
    activity_ref: Optional[str] = None  # Reference to activity for compensation
    attached_to: Optional[str] = None  # For boundary events
    cancelling: bool = True  # For boundary events, true if canceling the activity
    wait_for_completion: bool = False  # For compensation events


@dataclass(frozen=True)
class SequenceFlow:
    """Represents a BPMN sequence flow."""

    id: str
    source_ref: str
    target_ref: str
    condition_expression: Optional[str] = None


@dataclass(frozen=True)
class DataObject:
    """Represents a BPMN data object."""

    id: str
    name: Optional[str] = None
    type: Optional[str] = None


@dataclass(frozen=True)
class SubProcess(FlowNode):
    """Represents a BPMN subprocess."""

    nodes: List[FlowNode] = field(default_factory=list)
    flows: List[SequenceFlow] = field(default_factory=list)
    multi_instance: Optional[Dict[str, str]] = field(default_factory=dict)
