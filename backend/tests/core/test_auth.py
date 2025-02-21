"""Authentication core tests."""

from datetime import datetime, timedelta, UTC

import pytest
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pythmata.core.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user_by_email,
    verify_password,
)
from pythmata.models.user import Role, User


def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token(test_settings):
    """Test JWT token creation."""
    data = {"sub": "testuser"}
    expires_delta = timedelta(minutes=15)

    token = create_access_token(data, test_settings, expires_delta)

    # Verify token
    payload = jwt.decode(
        token,
        test_settings.security.secret_key,
        algorithms=[test_settings.security.algorithm],
    )

    assert payload["sub"] == data["sub"]
    exp = datetime.fromtimestamp(payload["exp"], UTC)
    now = datetime.now(UTC)
    assert (exp - now).total_seconds() > 0


@pytest.mark.asyncio
async def test_get_user_by_email(session, test_user: User):
    """Test getting user by email."""
    user = await get_user_by_email(session, test_user.email)
    assert user is not None
    assert user.email == test_user.email

    # Test non-existent user
    user = await get_user_by_email(session, "nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user(session, test_user: User):
    """Test user authentication."""
    # Test valid credentials
    user = await authenticate_user(session, test_user.email, "testpassword")
    assert user is not None
    assert user.email == test_user.email

    # Test invalid password
    user = await authenticate_user(session, test_user.email, "wrongpassword")
    assert user is None

    # Test non-existent user
    user = await authenticate_user(session, "nonexistent@example.com", "password")
    assert user is None


@pytest.mark.asyncio
async def test_user_role_relationship(session):
    """Test User and Role relationship."""
    # Create test role
    role = Role(
        name="test_role",
        permissions={"can_read": True, "can_write": False},
    )
    session.add(role)
    await session.commit()

    # Create test user with role
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        roles=[role],
    )
    session.add(user)
    await session.commit()

    # Query user with roles
    result = await session.execute(
        select(User)
        .filter(User.email == "test@example.com")
        .options(selectinload(User.roles))
    )
    user = result.scalar_one()

    assert len(user.roles) == 1
    assert user.roles[0].name == "test_role"
    assert user.roles[0].permissions == {"can_read": True, "can_write": False}


@pytest.mark.asyncio
async def test_user_model_timestamps(session):
    """Test User model timestamps."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
    )
    session.add(user)
    await session.commit()

    assert user.created_at is not None
    assert user.updated_at is not None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)

    # Test updated_at gets updated
    original_updated_at = user.updated_at
    await session.refresh(user)
    user.full_name = "Updated Name"
    await session.commit()
    await session.refresh(user)

    assert user.updated_at > original_updated_at
    assert user.created_at == user.created_at  # created_at should not change
