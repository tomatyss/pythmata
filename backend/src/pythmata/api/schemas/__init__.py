"""API schemas package."""

from pythmata.api.schemas.activity import ActivityLogResponse
from pythmata.api.schemas.base import ApiResponse, PaginatedResponse
from pythmata.api.schemas.llm import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    Message,
    XmlGenerationRequest,
    XmlModificationRequest,
    XmlResponse,
)
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
)
from pythmata.api.schemas.script import ScriptContent, ScriptResponse
from pythmata.api.schemas.token import TokenResponse

from pythmata.api.schemas.process.definition_version_migration import (
    ProcessMigrationRequest,
    ProcessMigrationResponse
)

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
    # Activity schemas
    "ActivityLogResponse",
    # Base schemas
    "ApiResponse",
    "PaginatedResponse",
    # LLM schemas
    "Message",
    "ChatRequest",
    "ChatResponse",
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatMessageResponse",
    "XmlGenerationRequest",
    "XmlModificationRequest",
    "XmlResponse",
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
    #Version Migration schemas
    "ProcessMigrationRequest",
    "ProcessMigrationResponse",
    # Script schemas
    "ScriptContent",
    "ScriptResponse",
    # Token schemas
    "TokenResponse",
]
