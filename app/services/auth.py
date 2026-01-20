"""User service layer - business logic for user operations."""

from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_password_hash, verify_password
from app.db.models.user import User


class UserAlreadyExistsError(Exception):
    """Raised when attempting to register a user that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


async def register_user(email: str, password: str, db: AsyncSession) -> User:
    """Register a new user.

    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        db: Database session

    Returns:
        The newly created User object

    Raises:
        UserAlreadyExistsError: If email is already registered
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise UserAlreadyExistsError("Email already registered")

    # Create new user
    hashed_password = get_password_hash(password)
    result = await db.execute(
        insert(User).values(email=email, hashed_password=hashed_password).returning(User)
    )
    new_user = result.scalar_one()
    await db.commit()

    return new_user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    """Authenticate a user with email and password.

    Args:
        email: User's email address
        password: Plain text password
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        InvalidCredentialsError: If email or password is incorrect
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect email or password")

    return user


async def delete_user(user_id: int, db: AsyncSession) -> int:
    """Delete a user and all associated data.

    Args:
        user_id: ID of the user to delete
        db: Database session

    Returns:
        The ID of the deleted user

    Note:
        This performs a hard delete. Associated data is removed via CASCADE.
    """
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return user_id
