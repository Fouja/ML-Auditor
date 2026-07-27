"""
JWT Authentication for Django Ninja.
"""

from typing import Any, Optional

from django.contrib.auth import get_user_model
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JWTAuth(HttpBearer):
    """
    JWT Authentication for Django Ninja.
    Validates Bearer token and returns user.
    """

    def authenticate(self, request, token: str) -> Optional[Any]:
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            user = User.objects.get(id=user_id)
            return user
        except Exception:
            return None
