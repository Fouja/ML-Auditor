"""
Shared pytest fixtures for ML-Auditor backend tests.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="testpass123",
    )


@pytest.fixture
def api_client():
    """Plain DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(client, user):
    """Django test client with JWT auth header."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {access}"
    return client
