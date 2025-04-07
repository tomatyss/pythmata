"""Process definition related schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pythmata.api.schemas.process.variables import ProcessVariableDefinition
from pythmata.api.schemas.process.versions import ProcessVersionResponse


class ProcessDefinitionBase(BaseModel):
    """Base schema for process definition."""

    name: str
    variable_definitions: List[ProcessVariableDefinition] = Field(default_factory=list)
    current_version_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionCreate(BaseModel):
    """Schema for creating a process definition."""

    name: str
    bpmn_xml: str  # Initial BPMN XML for the first version
    variable_definitions: Optional[List[ProcessVariableDefinition]] = Field(
        default_factory=list
    )
    notes: Optional[str] = None  # Optional notes for the first version

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionUpdate(BaseModel):
    """Schema for updating a process definition."""

    name: Optional[str] = None
    variable_definitions: Optional[List[ProcessVariableDefinition]] = None
    current_version_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionResponse(ProcessDefinitionBase):
    """Schema for process definition response."""

    id: UUID
    created_at: datetime
    active_instances: int = 0
    total_instances: int = 0
    current_version: Optional[ProcessVersionResponse] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
