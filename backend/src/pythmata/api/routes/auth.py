"""Authentication routes."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pythmata.api.dependencies import get_session
from pythmata.api.schemas.auth import Token, User, UserCreate
from pythmata.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
)
from pythmata.core.config import Settings, get_settings
from pythmata.models.user import User as UserModel

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Token:
    """Login user and return access token."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=settings.security.access_token_expire_minutes
    )
    access_token = create_access_token(
        data={"sub": str(user.id)},
        settings=settings,
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Register a new user."""
    # Check if user already exists
    db_user = await get_user_by_email(session, user_create.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user within a transaction
    async with session.begin_nested():  # Create savepoint
        hashed_password = get_password_hash(user_create.password)
        db_user = UserModel(
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            roles=[]  # Initialize empty roles list
        )
        session.add(db_user)
        await session.flush()  # Ensure user is created before commit

    # Commit the outer transaction
    await session.commit()

    # Load the user with relationships
    stmt = select(UserModel).where(UserModel.id == db_user.id).options(
        selectinload(UserModel.roles)
    )
    result = await session.execute(stmt)
    db_user = result.scalar_one()

    # Return through Pydantic model validation
    return User.model_validate(db_user)


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current user."""
    return current_user


@router.post("/logout")
async def logout() -> dict:
    """Logout user.

    Note: Since we're using JWTs, we don't actually need to do anything
    server-side. The client should remove the token from storage.
    """
    return {"message": "Successfully logged out"}
