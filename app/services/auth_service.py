"""User service layer - business logic for user operations."""

from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_password_hash, verify_password
from app.db.models.user import User


class AuthenticationError(Exception):
    """Base error for authentication-related failures."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class UserAlreadyExistsError(AuthenticationError):
    """Raised when attempting to register a user that already exists."""

    def __init__(self, message: str = "Email already registered") -> None:
        super().__init__(message, "user_exists")


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Incorrect email or password") -> None:
        super().__init__(message, "invalid_credentials")


class PasswordTooLongError(AuthenticationError):
    """Raised when password exceeds the maximum allowed length (72 bytes)."""

    def __init__(
        self, message: str = "Password must not exceed 72 bytes when UTF-8 encoded"
    ) -> None:
        super().__init__(message, "password_too_long")


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
        PasswordTooLongError: If password exceeds 72 bytes when UTF-8 encoded
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise UserAlreadyExistsError("Email already registered")

    # Create new user
    try:
        hashed_password = get_password_hash(password)
    except ValueError as e:
        raise PasswordTooLongError("Password must not exceed 72 bytes when UTF-8 encoded") from e

    try:
        result = await db.execute(
            insert(User).values(email=email, hashed_password=hashed_password).returning(User)
        )
        new_user = result.scalar_one()
    except IntegrityError as e:
        # Check if it's a unique constraint violation on email
        # asyncpg raises UniqueViolationError (error code 23505) for unique constraint violations
        error_str = str(e.orig).lower()
        if (
            "unique" in error_str
            or "duplicate" in error_str
            or "23505" in str(e.orig)  # PostgreSQL unique violation error code
            or "ix_users_email" in error_str  # Constraint name
        ):
            raise UserAlreadyExistsError("Email already registered") from e
        # Re-raise if it's a different integrity error
        raise

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
        PasswordTooLongError: If password exceeds 72 bytes when UTF-8 encoded
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError("Incorrect email or password")

    try:
        password_valid = verify_password(password, user.hashed_password)
    except ValueError as e:
        raise PasswordTooLongError("Password must not exceed 72 bytes when UTF-8 encoded") from e

    if not password_valid:
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
    return user_id
