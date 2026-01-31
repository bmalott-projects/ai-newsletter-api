from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Request model for user registration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "alex@example.com", "password": "Password123!"}]
        }
    )

    email: EmailStr = Field(
        ...,
        max_length=320,
        description="Valid email address",
        examples=["alex@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Password between 8 and 50 characters",
        examples=["Password123!"],
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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "alex@example.com", "password": "Password123!"}]
        }
    )

    email: EmailStr = Field(
        ...,
        max_length=320,
        description="Valid email address",
        examples=["alex@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Password between 8 and 50 characters",
        examples=["Password123!"],
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


class Token(BaseModel):
    """Response model for authentication token."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str = Field(
        ...,
        description="JWT access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field("bearer", description="Token type", examples=["bearer"])


class UserResponse(BaseModel):
    """Response model for user information."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [{"id": 123, "email": "alex@example.com"}]},
    )

    id: int = Field(..., examples=[123])
    email: str = Field(..., examples=["alex@example.com"])


class DeleteUserResponse(BaseModel):
    """Response model for user deletion."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"deleted_user_id": 123}]})

    deleted_user_id: int = Field(..., examples=[123])
