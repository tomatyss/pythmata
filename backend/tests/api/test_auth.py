"""Authentication API tests."""

import pytest
from fastapi import status
from httpx import AsyncClient

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
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "Password123!",
            "full_name": "New User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "hashed_password" not in data


async def test_register_duplicate_email(async_client: AsyncClient, test_user: User):
    """Test registration with existing email."""
    response = await async_client.post(
        "/auth/register",
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
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_invalid_credentials(async_client: AsyncClient, test_user: User):
    """Test login with invalid credentials."""
    response = await async_client.post(
        "/auth/login",
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
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    token = login_response.json()["access_token"]

    # Add role to user
    test_user.roles.append(test_role)
    await session.commit()

    # Get user info with token
    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == test_role.name


async def test_get_current_user_no_token(async_client: AsyncClient):
    """Test getting current user without token."""
    response = await async_client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_logout(async_client: AsyncClient, test_user: User):
    """Test user logout."""
    # First login to get token
    login_response = await async_client.post(
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
    )
    token = login_response.json()["access_token"]

    # Logout with token
    response = await async_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Successfully logged out"
