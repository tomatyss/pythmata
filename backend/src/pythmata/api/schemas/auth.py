"""Authentication schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Token schema."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data schema."""

    sub: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema."""

    password: str


class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class RoleBase(BaseModel):
    """Base role schema."""

    name: str
    permissions: Optional[dict] = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    pass


class RoleUpdate(RoleBase):
    """Role update schema."""

    name: Optional[str] = None


class Role(RoleBase):
    """Role schema."""

    id: UUID
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class User(UserBase):
    """User schema."""

    id: UUID
    roles: List[Role]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserInDB(User):
    """User in DB schema."""

    hashed_password: str
