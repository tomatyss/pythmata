"""Process instance related schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pythmata.api.schemas.process.variables import ProcessVariableDefinition, ProcessVariableValue
from pythmata.models.process import ProcessStatus


class ProcessInstanceCreate(BaseModel):
    """Schema for creating a process instance."""

    definition_id: UUID
    variables: Optional[Dict[str, ProcessVariableValue]] = Field(
        default_factory=dict,
        description="Dictionary of process variables. Each variable must match the process definition's variable definitions.",
    )

    model_config = ConfigDict(extra="forbid")

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
        var_defs = [ProcessVariableDefinition(**v) for v in variable_definitions]

        # Check required variables
        for var_def in var_defs:
            if var_def.required and var_def.name not in self.variables:
                if var_def.default_value is not None:
                    # Use default value if available
                    self.variables[var_def.name] = ProcessVariableValue(
                        type=var_def.type, value=var_def.default_value
                    )
                else:
                    raise ValueError(f"Required variable '{var_def.name}' is missing")

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
                        raise ValueError(f"Value for {var_name} must be an integer")
                    elif var_def.type == "float" and not isinstance(val, (int, float)):
                        raise ValueError(f"Value for {var_name} must be a float")
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
    definition_name: str
    status: ProcessStatus
    start_time: datetime
    end_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProcessInstanceFilter(BaseModel):
    """Schema for filtering process instances."""

    status: Optional[ProcessStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    definition_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")
