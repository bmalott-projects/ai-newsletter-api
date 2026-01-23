from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services.auth import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    authenticate_user,
    delete_user,
    register_user,
)

router = APIRouter()


class UserRegister(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., max_length=320, description="Valid email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Password must be between 8 and 50 characters",
    )

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate that password does not exceed 72 bytes when UTF-8 encoded.

        Note: We use a 50 character limit to ensure we stay under the 72-byte
        bcrypt limit even with multi-byte UTF-8 characters.
        """
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 50 characters")
        return v


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr = Field(..., max_length=320, description="Valid email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Password must be between 8 and 50 characters",
    )

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate that password does not exceed 72 bytes when UTF-8 encoded.

        Note: We use a 60 character limit to ensure we stay under the 72-byte
        bcrypt limit even with multi-byte UTF-8 characters.
        """
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 50 characters")
        return v


class Token(BaseModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user information."""

    id: int
    email: str
    model_config = ConfigDict(from_attributes=True)


class DeleteUserResponse(BaseModel):
    """Response model for user deletion."""

    deleted_user_id: int


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Register a new user."""
    try:
        new_user = await register_user(user_data.email, user_data.password, db)
        return UserResponse.model_validate(new_user)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate user and return JWT token."""
    try:
        user = await authenticate_user(credentials.email, credentials.password, db)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.delete("/me", response_model=DeleteUserResponse)
async def delete_me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DeleteUserResponse:
    """Delete the current authenticated user and all associated data."""
    deleted_id = await delete_user(current_user.id, db)
    return DeleteUserResponse(deleted_user_id=deleted_id)
