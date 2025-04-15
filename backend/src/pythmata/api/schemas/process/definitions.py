"""Process definition related schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pythmata.api.schemas.process.variables import ProcessVariableDefinition


class ProcessDefinitionBase(BaseModel):
    """Base schema for process definition."""

    name: str
    bpmn_xml: str
    version: int
    variable_definitions: List[ProcessVariableDefinition] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionCreate(BaseModel):
    """Schema for creating a process definition."""

    name: str
    bpmn_xml: str
    version: Optional[int] = 1  # Default to version 1 for new processes
    variable_definitions: Optional[List[ProcessVariableDefinition]] = Field(
        default_factory=list
    )

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionUpdate(BaseModel):
    """Schema for updating a process definition."""

    name: Optional[str] = None
    bpmn_xml: Optional[str] = None
    variable_definitions: Optional[List[ProcessVariableDefinition]] = None
    notes: Optional[str] = None  # Add notes for the new version
    expected_updated_at: datetime # Add timestamp for optimistic locking

    model_config = ConfigDict(extra="forbid")


class ProcessDefinitionResponse(ProcessDefinitionBase):
    """Schema for process definition response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    active_instances: int = 0
    total_instances: int = 0

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
