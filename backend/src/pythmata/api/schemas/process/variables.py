"""Process variable related schemas."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict


class ProcessVariableValidation(BaseModel):
    """Schema for process variable validation rules."""

    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None
    options: Optional[List[Any]] = None

    model_config = ConfigDict(extra="forbid")


class ProcessVariableDefinition(BaseModel):
    """Schema for process variable definition."""

    name: str
    type: Literal["string", "integer", "float", "boolean", "date", "json"]
    required: bool = True
    default_value: Optional[Any] = None
    validation: Optional[ProcessVariableValidation] = None
    label: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ProcessVariableValue(BaseModel):
    """Schema for process variable value."""

    type: Literal["string", "integer", "float", "boolean", "date", "json"]
    value: Union[str, int, float, bool, datetime, Dict[str, Any], List[Any]]

    model_config = ConfigDict(strict=True, extra="forbid")

    def model_dump_json(self, **kwargs):
        """Custom JSON serialization."""
        data = self.model_dump(**kwargs)
        if self.type == "date" and isinstance(self.value, datetime):
            data["value"] = self.value.isoformat()
        return data

    @property
    def is_valid_type(self) -> bool:
        """Check if value matches declared type."""
        if self.type == "string":
            return isinstance(self.value, str)
        elif self.type == "integer":
            return isinstance(self.value, int)
        elif self.type == "float":
            return isinstance(self.value, (int, float))
        elif self.type == "boolean":
            return isinstance(self.value, bool)
        elif self.type == "date":
            return isinstance(self.value, datetime)
        elif self.type == "json":
            return isinstance(self.value, (dict, list))
        return False

    def to_storage_format(self) -> Dict[str, Any]:
        """Convert to storage format for database and Redis."""
        # Convert datetime to ISO string for storage
        if self.type == "date" and isinstance(self.value, datetime):
            value = self.value.isoformat()
        else:
            value = self.value
        return {"value_type": self.type, "value_data": value}

    @classmethod
    def from_storage_format(cls, data: Dict[str, Any]) -> "ProcessVariableValue":
        """Create instance from storage format."""
        # Parse ISO string to datetime for date type
        if data["value_type"] == "date" and isinstance(data["value_data"], str):
            try:
                value = datetime.fromisoformat(data["value_data"])
            except ValueError:
                value = data["value_data"]  # Keep original if parsing fails
        else:
            value = data["value_data"]
        return cls(type=data["value_type"], value=value)
