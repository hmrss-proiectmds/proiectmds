"""
Pydantic schemas for authentication endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# ── Requests ──


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.human_player


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Responses ──


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    elo_rating: int
    created_at: datetime

    model_config = {"from_attributes": True}
