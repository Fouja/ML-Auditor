"""
Pydantic schemas for User API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema


class UserCreate(Schema):
    """Schema for creating a new user."""

    email: str
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserLogin(Schema):
    """Schema for user login."""

    email: str
    password: str


class UserResponse(Schema):
    """Schema for user response."""

    id: UUID
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_notifications: bool
    push_notifications: bool
    created_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at


class UserUpdate(Schema):
    """Schema for updating user."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class TokenResponse(Schema):
    """Schema for JWT token response."""

    access: str
    refresh: str
    token_type: str = "bearer"


class TokenRefresh(Schema):
    """Schema for token refresh."""

    refresh: str


class PushTokenSchema(Schema):
    """Schema for registering a push notification token."""

    token: str
    platform: str = "android"
    device_id: Optional[str] = ""
