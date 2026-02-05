"""API request and response schemas.

Import request/response models from the submodules (e.g. auth_request_models,
auth_response_models) or from this package for a single entry point.
"""

from __future__ import annotations

from app.api.schemas.auth_request_models import LoginUserRequest, RegisterUserRequest
from app.api.schemas.auth_response_models import (
    AccessTokenResponse,
    DeleteUserResponse,
    UserResponse,
)
from app.api.schemas.interests_request_models import InterestExtractionRequest
from app.api.schemas.interests_response_models import InterestExtractionResponse
from app.api.schemas.meta_response_models import HealthResponse

__all__ = [
    "AccessTokenResponse",
    "DeleteUserResponse",
    "HealthResponse",
    "InterestExtractionRequest",
    "InterestExtractionResponse",
    "LoginUserRequest",
    "RegisterUserRequest",
    "UserResponse",
]
