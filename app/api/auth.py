from __future__ import annotations
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter()


class UserRegister(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user information."""

    id: int
    email: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Register a new user."""
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    result = await db.execute(
        insert(User).values(email=user_data.email, hashed_password=hashed_password).returning(User)
    )
    new_user = result.scalar_one()
    await db.commit()

    return UserResponse(id=new_user.id, email=new_user.email)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate user and return JWT token."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse(id=current_user.id, email=current_user.email)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    """Delete the current authenticated user and all associated data."""
    await db.execute(delete(User).where(User.id == current_user.id))
    await db.commit()
