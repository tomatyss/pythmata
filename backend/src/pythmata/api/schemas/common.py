"""Common schema definitions."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema for paginated response."""

    items: List[T]
    total: int
    page: int
    pageSize: int
    totalPages: int

    model_config = ConfigDict(extra="forbid")


class ApiResponse(BaseModel, Generic[T]):
    """Schema for API response."""

    data: T

    model_config = ConfigDict(extra="forbid") 