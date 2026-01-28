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
from app.core.errors import ErrorResponse, build_http_error
from app.db.models.user import User
from app.db.session import get_db, get_db_transaction
from app.services.auth_service import (
    AuthenticationError,
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
async def register(
    user_data: UserRegister, db: AsyncSession = Depends(get_db_transaction)
) -> UserResponse:
    """Register a new user."""
    try:
        new_user = await register_user(user_data.email, user_data.password, db)
        return UserResponse.model_validate(new_user)
    except AuthenticationError as e:
        if isinstance(e, UserAlreadyExistsError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(e, PasswordTooLongError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        raise build_http_error(
            status_code=status_code,
            error=e.error_code,
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
    except AuthenticationError as e:
        if isinstance(e, InvalidCredentialsError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(e, PasswordTooLongError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        headers = (
            {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
        )
        raise build_http_error(
            status_code=status_code,
            error=e.error_code,
            message=str(e),
            headers=headers,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_transaction),
) -> DeleteUserResponse:
    """Delete the current authenticated user and all associated data."""
    deleted_id = await delete_user(current_user.id, db)
    return DeleteUserResponse(deleted_user_id=deleted_id)
