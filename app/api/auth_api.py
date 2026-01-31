from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
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
from app.core.rate_limit import (
    AUTH_DELETE_RATE_LIMIT,
    AUTH_LOGIN_RATE_LIMIT,
    AUTH_REGISTER_RATE_LIMIT,
    limit,
    rate_limit_ip_key,
    rate_limit_user_or_ip_key,
)
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
    summary="Register user",
    description="Create a new user account with email and password.",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Email already registered",
            "content": {
                "application/json": {
                    "examples": {
                        "user_exists": {
                            "summary": "User already exists",
                            "value": {
                                "error": "user_exists",
                                "message": "Email already registered",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid registration input",
            "content": {
                "application/json": {
                    "examples": {
                        "password_too_long": {
                            "summary": "Password too long",
                            "value": {
                                "error": "password_too_long",
                                "message": "Password must not exceed 72 bytes when UTF-8 encoded",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        },
    },
)
@limit(AUTH_REGISTER_RATE_LIMIT, key_func=rate_limit_ip_key)
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db_transaction),
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
    summary="Log in",
    description="Authenticate credentials and return a bearer access token.",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Invalid email or password",
                            "value": {
                                "error": "invalid_credentials",
                                "message": "Incorrect email or password",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid login input",
            "content": {
                "application/json": {
                    "examples": {
                        "password_too_long": {
                            "summary": "Password too long",
                            "value": {
                                "error": "password_too_long",
                                "message": "Password must not exceed 72 bytes when UTF-8 encoded",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        },
    },
)
@limit(AUTH_LOGIN_RATE_LIMIT, key_func=rate_limit_ip_key)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
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
    summary="Get current user",
    description="Return the user for the provided bearer token.",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid token",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Unauthorized",
                            "value": {
                                "error": "unauthorized",
                                "message": "Could not validate credentials",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        },
    },
)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.delete(
    "/me",
    summary="Delete current user",
    description="Delete the current user and associated data.",
    response_model=DeleteUserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid token",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Unauthorized",
                            "value": {
                                "error": "unauthorized",
                                "message": "Could not validate credentials",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        },
    },
)
@limit(AUTH_DELETE_RATE_LIMIT, key_func=rate_limit_user_or_ip_key)
async def delete_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_transaction),
) -> DeleteUserResponse:
    """Delete the current authenticated user and all associated data."""
    deleted_id = await delete_user(current_user.id, db)
    return DeleteUserResponse(deleted_user_id=deleted_id)
