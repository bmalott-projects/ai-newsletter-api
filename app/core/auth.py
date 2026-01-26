from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import build_http_error
from app.db.models.user import User
from app.db.session import get_db

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token extractor (OAuth2PasswordBearer is FastAPI's helper for extracting
# Bearer tokens from Authorization headers - we're using JWT, not OAuth2)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    # bcrypt only considers the first 72 bytes of the password; enforce this to avoid
    # silent truncation and align with unit tests that expect a ValueError.
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes when UTF-8 encoded.")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    # Mirror the same 72-byte limit check used when hashing to avoid verifying
    # truncated passwords as valid.
    if len(plain_password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes when UTF-8 encoded.")
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to get the current authenticated user."""
    credentials_exception = build_http_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        error="unauthorized",
        message="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id_value = payload.get("sub")
    if not isinstance(user_id_value, str):
        raise credentials_exception

    try:
        user_id = int(user_id_value)
    except (ValueError, TypeError):
        raise credentials_exception from None

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
