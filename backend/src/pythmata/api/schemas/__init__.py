"""API schemas package."""

from .auth import (
    Role,
    RoleCreate,
    RoleUpdate,
    Token,
    TokenData,
    User,
    UserCreate,
    UserInDB,
    UserUpdate,
)

from pythmata.api.schemas.base import ApiResponse, PaginatedResponse
from pythmata.api.schemas.process import (

    ProcessDefinitionBase,
    ProcessDefinitionCreate,
    ProcessDefinitionResponse,
    ProcessDefinitionUpdate,
    ProcessInstanceCreate,
    ProcessInstanceFilter,
    ProcessInstanceResponse,
    ProcessStats,
    ProcessVariableDefinition,
    ProcessVariableValidation,
    ProcessVariableValue,
    ScriptContent,
    ScriptResponse,
    TokenResponse,
)


from pythmata.api.schemas.script import ScriptContent, ScriptResponse
from pythmata.api.schemas.token import TokenResponse

__all__ = [
    # Auth schemas
    "Token",
    "TokenData",
    "User",
    "UserCreate",
    "UserUpdate",
    "Role",
    "RoleCreate",
    "RoleUpdate",
    "UserInDB",
    # Base schemas
    "ApiResponse",
    "PaginatedResponse",
    # Process schemas
    "ProcessDefinitionBase",
    "ProcessDefinitionCreate",
    "ProcessDefinitionResponse",
    "ProcessDefinitionUpdate",
    "ProcessInstanceCreate",
    "ProcessInstanceFilter",
    "ProcessInstanceResponse",
    "ProcessStats",
    "ProcessVariableDefinition",
    "ProcessVariableValidation",
    "ProcessVariableValue",
    # Script schemas
    "ScriptContent",
    "ScriptResponse",
    # Token schemas
    "TokenResponse",
]
