"""
User API endpoints for ML-Auditor.
"""

from typing import List

from django.contrib.auth import authenticate, get_user_model
from ninja import Router
from ninja.errors import HttpError
from rest_framework_simplejwt.tokens import RefreshToken

from .schemas import (
    PushTokenSchema,
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

User = get_user_model()
router = Router()


@router.post("/register", response=TokenResponse, auth=None)
def register(request, payload: UserCreate):
    """Register a new user."""
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email already exists")

    user = User.objects.create_user(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        first_name=payload.first_name or "",
        last_name=payload.last_name or "",
    )

    tokens = RefreshToken.for_user(user)
    return TokenResponse(
        access=str(tokens.access_token),
        refresh=str(tokens),
    )


@router.post("/login", response=TokenResponse, auth=None)
def login(request, payload: UserLogin):
    """Login with email and password."""
    user = authenticate(email=payload.email, password=payload.password)
    if not user:
        raise HttpError(401, "Invalid credentials")

    tokens = RefreshToken.for_user(user)
    return TokenResponse(
        access=str(tokens.access_token),
        refresh=str(tokens),
    )


@router.post("/refresh", response=TokenResponse, auth=None)
def refresh_token(request, payload: TokenRefresh):
    """Refresh access token."""
    try:
        refresh = RefreshToken(payload.refresh)
        return TokenResponse(
            access=str(refresh.access_token),
            refresh=str(refresh),
        )
    except Exception:
        raise HttpError(401, "Invalid refresh token")


@router.get("/me", response=UserResponse)
def get_current_user(request):
    """Get current authenticated user."""
    return request.auth


@router.put("/me", response=UserResponse)
def update_current_user(request, payload: UserUpdate):
    """Update current user profile."""
    user = request.auth
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)
    user.save()
    return user


@router.get("/", response=List[UserResponse])
def list_users(request):
    """List all users (admin only)."""
    if not request.auth.is_staff:
        raise HttpError(403, "Not authorized")
    return User.objects.all()


@router.get("/{user_id}", response=UserResponse)
def get_user(request, user_id: str):
    """Get user by ID (admin only)."""
    if not request.auth.is_staff:
        raise HttpError(403, "Not authorized")
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")


@router.post("/push-token")
def register_push_token(request, payload: PushTokenSchema):
    """Register or update a push notification token for the current user."""
    from .models import PushToken

    user = request.auth
    PushToken.objects.update_or_create(
        user=user,
        token=payload.token,
        defaults={
            "platform": payload.platform,
            "device_id": payload.device_id or "",
            "is_active": True,
        },
    )
    return {"success": True}


@router.delete("/push-token/{token}")
def unregister_push_token(request, token: str):
    """Deactivate a push notification token."""
    from .models import PushToken

    PushToken.objects.filter(user=request.auth, token=token).update(is_active=False)
    return {"success": True}
