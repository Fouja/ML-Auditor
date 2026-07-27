"""
Request specs for API endpoints.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def auth_client(user):
    """DRF API client with JWT."""
    client = APIClient()
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
class TestUsersAPI:
    def test_register(self):
        client = APIClient()
        resp = client.post(
            "/api/users/register",
            {
                "email": "new@test.com",
                "username": "newuser",
                "password": "pass12345",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        assert resp.status_code in (200, 201)

    def test_login(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(email="login@test.com", username="login", password="pass123")
        client = APIClient()
        resp = client.post(
            "/api/users/login",
            {"email": "login@test.com", "password": "pass123"},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.json()


@pytest.mark.django_db
class TestWorkspaceAPI:
    def test_list_tasks(self, auth_client):
        resp = auth_client.get("/api/workspace/tasks")
        assert resp.status_code == 200

    def test_create_task(self, auth_client):
        resp = auth_client.post(
            "/api/workspace/tasks",
            {"title": "API Task", "status": "todo", "priority": "medium"},
            format="json",
        )
        assert resp.status_code in (200, 201)

    def test_list_events(self, auth_client):
        resp = auth_client.get("/api/workspace/events")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestIntegrationAPI:
    def test_status(self, auth_client):
        resp = auth_client.get("/api/integrations/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "plaid" in data
        assert "canva" in data

    def test_email_status(self, auth_client):
        resp = auth_client.get("/api/integrations/email/status")
        assert resp.status_code == 200

    def test_plaid_status(self, auth_client):
        resp = auth_client.get("/api/integrations/plaid/status")
        assert resp.status_code == 200

    def test_canva_status(self, auth_client):
        resp = auth_client.get("/api/integrations/canva/status")
        assert resp.status_code == 200

    def test_kijiji_search(self, auth_client):
        resp = auth_client.post(
            "/api/integrations/kijiji/search",
            {"query": "test"},
            format="json",
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestAgentAPI:
    def test_status(self, auth_client):
        resp = auth_client.get("/api/agents/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data

    def test_list_workflows(self, auth_client):
        resp = auth_client.get("/api/agents/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["workflows"]) == 4

    def test_notification_prefs(self, auth_client):
        resp = auth_client.get("/api/agents/notifications/preferences")
        assert resp.status_code == 200

    def test_chat(self, auth_client):
        resp = auth_client.post(
            "/api/agents/chat",
            {"content": "Hello", "agent_type": "general"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["agent_type"] == "general"
