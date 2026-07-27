"""
Unit tests for Django models.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            email="unit@test.com", username="unit", password="pass123"
        )
        assert user.email == "unit@test.com"
        assert user.check_password("pass123")
        assert user.is_active is True

    def test_user_str(self):
        user = User.objects.create_user(
            email="str@test.com", username="strtest", password="pass123"
        )
        assert str(user) == "str@test.com"

    def test_user_uuid_primary_key(self):
        user = User.objects.create_user(
            email="uuid@test.com", username="uuidtest", password="pass123"
        )
        assert user.id is not None
        assert isinstance(user.id, str) or hasattr(user.id, "hex")

    def test_user_imap_fields(self):
        user = User.objects.create_user(
            email="imap@test.com", username="imaptest", password="pass123"
        )
        user.email_provider = "gmail"
        user.email_imap_host = "imap.gmail.com"
        user.email_smtp_host = "smtp.gmail.com"
        user.email_imap_password = "apppassword"
        user.save()

        user.refresh_from_db()
        assert user.email_provider == "gmail"
        assert user.email_imap_host == "imap.gmail.com"

    def test_user_canva_fields(self):
        user = User.objects.create_user(
            email="canva@test.com", username="canvatest", password="pass123"
        )
        user.canva_access_token = "test_token"
        user.save()
        user.refresh_from_db()
        assert user.canva_access_token == "test_token"


@pytest.mark.django_db
class TestWorkspaceModels:
    def test_create_task(self, user):
        from apps.workspace.models import Task
        task = Task.objects.create(
            user=user, title="Test Task", status="todo", priority="high"
        )
        assert task.title == "Test Task"
        assert task.status == "todo"
        assert task.priority == "high"

    def test_task_str(self, user):
        from apps.workspace.models import Task
        task = Task.objects.create(user=user, title="My Task", status="todo")
        assert "My Task" in str(task)

    def test_create_calendar_event(self, user):
        from apps.workspace.models import CalendarEvent
        event = CalendarEvent.objects.create(
            user=user,
            title="Meeting",
            start_time="2026-08-01T10:00:00Z",
            end_time="2026-08-01T11:00:00Z",
        )
        assert event.title == "Meeting"


@pytest.mark.django_db
class TestIntegrationModels:
    def test_integration_connection(self, user):
        from apps.integrations.models import IntegrationConnection
        conn = IntegrationConnection.objects.create(
            user=user, service="email", status="active"
        )
        assert conn.service == "email"
        assert conn.status == "active"

    def test_sync_log(self, user):
        from apps.integrations.models import IntegrationConnection, SyncLog
        conn = IntegrationConnection.objects.create(
            user=user, service="gmail", status="active"
        )
        log = SyncLog.objects.create(
            connection=conn, success=True, items_synced=10
        )
        assert log.success is True
        assert log.items_synced == 10


@pytest.mark.django_db
class TestAlertModel:
    def test_create_alert(self, user):
        from apps.alerts.models import AgentAlert
        alert = AgentAlert.objects.create(
            user=user,
            title="Critical Alert",
            description="Something bad",
            severity="critical",
        )
        assert alert.severity == "critical"
        assert alert.status == "pending"
