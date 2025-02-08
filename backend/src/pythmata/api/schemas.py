from datetime import datetime
from typing import Dict, Generic, List, Optional, TypeVar, Union, Any
from uuid import UUID

from pydantic import BaseModel, Field

from pythmata.models.process import ProcessStatus


class ProcessDefinitionBase(BaseModel):
    """Base schema for process definition."""

    name: str
    bpmn_xml: str
    version: int


class ProcessDefinitionCreate(BaseModel):
    """Schema for creating a process definition."""

    name: str
    bpmn_xml: str
    version: Optional[int] = 1  # Default to version 1 for new processes


class ProcessDefinitionUpdate(BaseModel):
    """Schema for updating a process definition."""

    name: Optional[str] = None
    bpmn_xml: Optional[str] = None
    version: Optional[int] = None  # Allow updating version


class ProcessDefinitionResponse(ProcessDefinitionBase):
    """Schema for process definition response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # Allow ORM model conversion


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema for paginated response."""

    items: List[T]
    total: int
    page: int
    pageSize: int
    totalPages: int


class ApiResponse(BaseModel, Generic[T]):
    """Schema for API response."""

    data: T


class ProcessVariableValue(BaseModel):
    """Schema for process variable value."""
    type: str
    value: Union[str, int, float, bool, dict]

    def to_storage_format(self) -> Dict[str, Any]:
        """Convert to storage format for database and Redis."""
        return {
            "value_type": self.type,
            "value_data": self.value
        }

    @classmethod
    def from_storage_format(cls, data: Dict[str, Any]) -> "ProcessVariableValue":
        """Create instance from storage format."""
        return cls(
            type=data["value_type"],
            value=data["value_data"]
        )


class ProcessInstanceCreate(BaseModel):
    """Schema for creating a process instance."""

    definition_id: UUID
    variables: Optional[Dict[str, ProcessVariableValue]] = Field(
        default_factory=dict,
        description="Dictionary of process variables. Each variable has a type and value.",
    )


class ProcessInstanceResponse(BaseModel):
    """Schema for process instance response."""

    id: UUID
    definition_id: UUID
    status: ProcessStatus
    start_time: datetime
    end_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProcessInstanceFilter(BaseModel):
    """Schema for filtering process instances."""

    status: Optional[ProcessStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    definition_id: Optional[UUID] = None


class ProcessStats(BaseModel):
    """Schema for process statistics."""

    total_instances: int
    status_counts: Dict[ProcessStatus, int]
    average_completion_time: Optional[float]  # in seconds
    error_rate: float  # percentage
    active_instances: int


class ScriptContent(BaseModel):
    """Schema for script content."""

    content: str
    version: int = 1


class ScriptResponse(BaseModel):
    """Schema for script response."""

    id: UUID
    process_def_id: UUID
    node_id: str
    content: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
