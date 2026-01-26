from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import (
    DeleteUserResponse,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.core.auth import create_access_token, get_current_user
from app.core.errors import build_http_error
from app.db.models.user import User
from app.db.session import get_db
from app.services.auth import (
    InvalidCredentialsError,
    PasswordTooLongError,
    UserAlreadyExistsError,
    authenticate_user,
    delete_user,
    register_user,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Register a new user."""
    try:
        new_user = await register_user(user_data.email, user_data.password, db)
        return UserResponse.model_validate(new_user)
    except UserAlreadyExistsError as e:
        raise build_http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="user_exists",
            message=str(e),
        ) from e
    except PasswordTooLongError as e:
        raise build_http_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error="password_too_long",
            message=str(e),
        ) from e


@router.post(
    "/login",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate user and return JWT token."""
    try:
        user = await authenticate_user(credentials.email, credentials.password, db)
    except InvalidCredentialsError as e:
        raise build_http_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_credentials",
            message=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except PasswordTooLongError as e:
        raise build_http_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error="password_too_long",
            message=str(e),
        ) from e

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.delete(
    "/me",
    response_model=DeleteUserResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
async def delete_me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DeleteUserResponse:
    """Delete the current authenticated user and all associated data."""
    deleted_id = await delete_user(current_user.id, db)
    return DeleteUserResponse(deleted_user_id=deleted_id)
