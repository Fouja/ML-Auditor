"""
Authorization policies for ML-Auditor.
Object-level permissions for resource access control.
"""

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

User = get_user_model()


class IsOwner(BasePermission):
    """
    Permission to only allow owners of an object.
    """

    def has_object_permission(self, request, view, obj):
        # Check if object has a user field
        if hasattr(obj, "user"):
            return obj.user == request.auth
        return False


class IsAdminOrReadOnly(BasePermission):
    """
    Permission to allow admins full access, others read-only.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.auth and request.auth.is_staff


class IsAdminUser(BasePermission):
    """
    Permission to only allow admin users.
    """

    def has_permission(self, request, view):
        return request.auth and request.auth.is_staff


class IsAuthenticated(BasePermission):
    """
    Permission to only allow authenticated users.
    """

    def has_permission(self, request, view):
        return request.auth is not None


class IsOwnerOrAdmin(BasePermission):
    """
    Permission to allow owners or admins.
    """

    def has_object_permission(self, request, view, obj):
        if request.auth.is_staff:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.auth
        return False


class HasOAuthToken(BasePermission):
    """
    Permission to check if user has required OAuth token.
    """

    def __init__(self, provider):
        self.provider = provider

    def has_permission(self, request, view):
        if not request.auth:
            return False

        token_field = f"{self.provider}_access_token"
        return hasattr(request.auth, token_field) and getattr(
            request.auth, token_field, None
        )


class HasPlaidToken(HasOAuthToken):
    """Permission to check Plaid token."""

    def __init__(self):
        super().__init__("plaid")


class HasGoogleToken(HasOAuthToken):
    """Permission to check Google token."""

    def __init__(self):
        super().__init__("google")
