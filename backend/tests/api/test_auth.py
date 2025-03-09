"""Authentication API tests."""

import pytest
from fastapi import status
from httpx import AsyncClient

from pythmata.api.schemas.auth import Token
from pythmata.api.schemas.auth import User as UserSchema
from pythmata.core.auth import get_password_hash
from pythmata.models.user import Role, User


@pytest.fixture
async def test_user(session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def test_role(session):
    """Create a test role."""
    role = Role(
        name="test_role",
        permissions={"can_read": True, "can_write": False},
    )
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def test_register_user(async_client: AsyncClient):
    """Test user registration."""
    # Test data
    user_data = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "New User",
    }

    response = await async_client.post(
        "/api/auth/register",
        json=user_data,
    )

    # Check status code
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), "Registration should succeed"

    # Validate response against schema
    user = UserSchema.model_validate(response.json())

    # Verify user data
    assert user.email == user_data["email"], "Email should match"
    assert user.full_name == user_data["full_name"], "Full name should match"
    assert user.is_active, "User should be active"
    assert isinstance(user.roles, list), "Roles should be a list"
    assert len(user.roles) == 0, "New user should have no roles"
    assert "hashed_password" not in response.json(), "Password should not be exposed"

    # Verify timestamps and ID
    assert user.id is not None, "User should have an ID"
    assert user.created_at is not None, "Created timestamp should be set"
    assert user.updated_at is not None, "Updated timestamp should be set"


async def test_register_duplicate_email(async_client: AsyncClient, test_user: User):
    """Test registration with existing email."""
    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": test_user.email,
            "password": "Password123!",
            "full_name": "Another User",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_login_success(async_client: AsyncClient, test_user: User):
    """Test successful login."""
    response = await async_client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    assert response.status_code == status.HTTP_200_OK, "Login should succeed"

    # Validate response against schema
    token = Token.model_validate(response.json())

    # Verify token data
    assert token.access_token, "Access token should be present"
    assert token.token_type == "bearer", "Token type should be bearer"


async def test_login_invalid_credentials(async_client: AsyncClient, test_user: User):
    """Test login with invalid credentials."""
    response = await async_client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_current_user(
    async_client: AsyncClient, session, test_user: User, test_role: Role
):
    """Test getting current user info."""
    # First login to get token
    login_response = await async_client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    token = Token.model_validate(login_response.json())

    # Add role to user
    await session.refresh(test_user, ["roles"])
    test_user.roles.append(test_role)
    await session.commit()

    # Get user info with token
    response = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK, "Should get user info"

    # Validate response against schema
    user = UserSchema.model_validate(response.json())

    # Verify user data
    assert user.email == test_user.email, "Email should match"
    assert user.full_name == test_user.full_name, "Full name should match"
    assert len(user.roles) == 1, "Should have one role"
    assert user.roles[0].name == test_role.name, "Role name should match"


async def test_get_current_user_no_token(async_client: AsyncClient):
    """Test getting current user without token."""
    response = await async_client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_logout(async_client: AsyncClient, test_user: User):
    """Test user logout."""
    # First login to get token
    login_response = await async_client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    token = Token.model_validate(login_response.json())

    # Logout with token
    response = await async_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK, "Logout should succeed"
    data = response.json()
    assert data["message"] == "Successfully logged out", "Should return success message"
