from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field

from pythmata.models.process import ProcessStatus


class ProcessVariableValidation(BaseModel):
    """Schema for process variable validation rules."""

    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None
    options: Optional[List[Any]] = None


class ProcessVariableDefinition(BaseModel):
    """Schema for process variable definition."""

    name: str
    type: Literal["string", "integer", "float", "boolean", "date", "json"]
    required: bool = True
    default_value: Optional[Any] = None
    validation: Optional[ProcessVariableValidation] = None
    label: str
    description: Optional[str] = None


class ProcessDefinitionBase(BaseModel):
    """Base schema for process definition."""

    name: str
    bpmn_xml: str
    version: int
    variable_definitions: List[ProcessVariableDefinition] = Field(
        default_factory=list)


class ProcessDefinitionCreate(BaseModel):
    """Schema for creating a process definition."""

    name: str
    bpmn_xml: str
    version: Optional[int] = 1  # Default to version 1 for new processes
    variable_definitions: Optional[List[ProcessVariableDefinition]] = Field(
        default_factory=list
    )


class ProcessDefinitionUpdate(BaseModel):
    """Schema for updating a process definition."""

    name: Optional[str] = None
    bpmn_xml: Optional[str] = None
    version: Optional[int] = None  # Allow updating version
    variable_definitions: Optional[List[ProcessVariableDefinition]] = None


class ProcessDefinitionResponse(ProcessDefinitionBase):
    """Schema for process definition response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    active_instances: int = 0
    total_instances: int = 0

    model_config = {"from_attributes": True, "populate_by_name": True}  # Allow ORM model conversion and populate by field name


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

    type: Literal["string", "integer", "float", "boolean", "date", "json"]
    value: Union[str, int, float, bool, datetime, Dict[str, Any], List[Any]]

    model_config = {
        "strict": True,  # Ensure strict type checking
        "json_encoders": {
            datetime: lambda v: v.isoformat(),  # Handle datetime serialization
        },
    }

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


class ProcessInstanceCreate(BaseModel):
    """Schema for creating a process instance."""

    definition_id: UUID
    variables: Optional[Dict[str, ProcessVariableValue]] = Field(
        default_factory=dict,
        description="Dictionary of process variables. Each variable must match the process definition's variable definitions.",
    )

    def validate_variables(self, variable_definitions: List[Dict[str, Any]]) -> None:
        """Validate variables against process definition.

        Args:
            variable_definitions: List of variable definitions from process definition

        Raises:
            ValueError: If variables don't match definitions
        """
        if not self.variables:
            self.variables = {}

        # Convert dictionary definitions to ProcessVariableDefinition objects
        var_defs = [ProcessVariableDefinition(
            **v) for v in variable_definitions]

        # Check required variables
        for var_def in var_defs:
            if var_def.required and var_def.name not in self.variables:
                if var_def.default_value is not None:
                    # Use default value if available
                    self.variables[var_def.name] = ProcessVariableValue(
                        type=var_def.type, value=var_def.default_value
                    )
                else:
                    raise ValueError(
                        f"Required variable '{var_def.name}' is missing")

        # Create map for validation
        var_def_map = {v.name: v for v in var_defs}

        # Validate provided variables
        for var_name, var_value in self.variables.items():
            if var_name not in var_def_map:
                raise ValueError(f"Unknown variable '{var_name}'")

            var_def = var_def_map[var_name]
            if var_value.type != var_def.type:
                raise ValueError(
                    f"Variable '{var_name}' has wrong type. Expected {var_def.type}, got {var_value.type}"
                )

            # Validate type first
            if not var_value.is_valid_type:
                raise ValueError(
                    f"Variable '{var_name}' has invalid value type. "
                    f"Expected {var_def.type}, got {type(var_value.value).__name__}"
                )

            # Validate value based on rules
            if var_def.validation:
                val = var_value.value
                if var_def.type in ["integer", "float"]:
                    if (
                        var_def.validation.min is not None
                        and val < var_def.validation.min
                    ) or (
                        var_def.validation.max is not None
                        and val > var_def.validation.max
                    ):
                        raise ValueError(
                            f"Variable '{var_name}' value {val} is outside allowed range "
                            f"[{var_def.validation.min}, {var_def.validation.max}]"
                        )
                    # Additional type validation
                    if var_def.type == "integer" and not isinstance(val, int):
                        raise ValueError(
                            f"Value for {var_name} must be an integer")
                    elif var_def.type == "float" and not isinstance(val, (int, float)):
                        raise ValueError(
                            f"Value for {var_name} must be a float")
                elif var_def.type == "string" and var_def.validation.pattern:
                    import re

                    if not re.match(var_def.validation.pattern, str(val)):
                        raise ValueError(
                            f"Variable '{var_name}' value does not match pattern {var_def.validation.pattern}"
                        )
                if var_def.validation.options and val not in var_def.validation.options:
                    raise ValueError(
                        f"Variable '{var_name}' value must be one of {var_def.validation.options}"
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
