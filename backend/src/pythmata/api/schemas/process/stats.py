"""Process statistics related schemas."""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from pythmata.models.process import ProcessStatus


class ProcessStats(BaseModel):
    """Schema for process statistics."""

    total_instances: int
    status_counts: Dict[ProcessStatus, int]
    average_completion_time: Optional[float]  # in seconds
    error_rate: float  # percentage
    active_instances: int

    model_config = ConfigDict(extra="forbid")
