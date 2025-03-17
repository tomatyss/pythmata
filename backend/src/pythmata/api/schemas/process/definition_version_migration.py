"""Process migration related schemas."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcessMigrationRequest(BaseModel):
    """Schema for process migration request."""

    process_id: str
    source_version: int
    target_version: int

    model_config = ConfigDict(extra="forbid")

    model_config = ConfigDict(extra="forbid")


class ProcessMigrationResponse(BaseModel):
    """Schema for process migration response."""

    migrated_instances: int = Field(default=0, description="Number of successfully migrated instances.")
    failed_instances: int = Field(default=0, description="Number of instances that failed to migrate.")