"""Request models for auth API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class _UserAuthRequestBase(BaseModel):
    """Shared base for user authentication request models."""

    email: EmailStr = Field(..., max_length=320, description="Valid email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Password between 8 and 50 characters",
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


class RegisterUserRequest(_UserAuthRequestBase):
    """Request model for user registration."""


class LoginUserRequest(_UserAuthRequestBase):
    """Request model for user login."""
