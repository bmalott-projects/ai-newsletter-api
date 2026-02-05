"""Response models for auth API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AccessTokenResponse(BaseModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class DeleteUserResponse(BaseModel):
    """Response model for user deletion."""

    deleted_user_id: int
