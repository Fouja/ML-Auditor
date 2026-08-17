"""
Tests for agent services: workflows, tool executor, notifications.
"""

import pytest


@pytest.mark.django_db
class TestWorkflows:
    def test_confirm_rdv_workflow(self, user):
        from apps.agents.services.workflows import workflow_confirm_rdv

        result = workflow_confirm_rdv(
            user,
            {
                "title": "Doctor Visit",
                "start_time": "2026-08-15T14:00:00",
                "end_time": "2026-08-15T15:00:00",
                "location": "Clinic",
            },
        )
        assert result.workflow == "confirm_rdv"
        assert len(result.actions) > 0

    def test_financial_anomaly_workflow(self, user):
        from apps.agents.services.workflows import workflow_financial_anomaly

        result = workflow_financial_anomaly(
            user,
            {
                "transaction_name": "Suspicious Charge",
                "amount": 500.00,
                "category": "Unknown",
                "confidence": 0.85,
                "description": "Unusual transaction",
            },
        )
        assert result.workflow == "financial_anomaly"
        assert result.success is True

    def test_email_auto_reply_workflow(self, user):
        from apps.agents.services.workflows import workflow_email_auto_reply

        result = workflow_email_auto_reply(
            user,
            {
                "subject": "Meeting Request",
                "from": "sender@test.com",
                "body": "Can we meet?",
            },
        )
        assert result.workflow == "email_auto_reply"

    def test_kijiji_negotiation_workflow(self, user):
        from apps.agents.services.workflows import workflow_kijiji_negotiation

        result = workflow_kijiji_negotiation(
            user,
            {
                "title": "Used Laptop",
                "price": 300,
            },
        )
        assert result.workflow == "kijiji_negotiation"
        assert len(result.actions) == 3

    def test_unknown_workflow(self, user):
        from apps.agents.services.workflows import execute_workflow

        result = execute_workflow("nonexistent", user, {})
        assert result.success is False


@pytest.mark.django_db
class TestNotifications:
    def test_severity_rules(self):
        from apps.agents.services.notifications import SEVERITY_RULES

        assert "critical" in SEVERITY_RULES
        assert "email" in SEVERITY_RULES["critical"]["notify_channels"]

    def test_determine_severity_high(self):
        from apps.agents.services.notifications import AlertRouter

        assert AlertRouter.determine_severity({"confidence": 0.95}) == "critical"

    def test_determine_severity_medium(self):
        from apps.agents.services.notifications import AlertRouter

        assert AlertRouter.determine_severity({"confidence": 0.5}) == "medium"

    def test_determine_severity_explicit(self):
        from apps.agents.services.notifications import AlertRouter

        assert AlertRouter.determine_severity({"severity": "high"}) == "high"

    def test_notification_prefs_get(self, user):
        from apps.agents.services.notifications import NotificationPreferences

        prefs = NotificationPreferences.get_preferences(user)
        assert "email_notifications" in prefs
        assert "push_notifications" in prefs

    def test_notification_prefs_update(self, user):
        from apps.agents.services.notifications import NotificationPreferences

        updated = NotificationPreferences.update_preferences(
            user,
            {
                "email_notifications": False,
            },
        )
        assert updated["email_notifications"] is False


@pytest.mark.asyncio
class TestToolExecutor:
    async def test_create_task_tool(self, user):
        from unittest.mock import AsyncMock, MagicMock, patch

        from apps.agents.services.tool_executor import ToolExecutor

        executor = ToolExecutor(user)
        mock_task = MagicMock()
        mock_task.id = "test-uuid-123"
        mock_task.title = "Tool Test"
        with patch("apps.agents.services.tool_executor.sync_to_async") as mock_sync:
            mock_sync.return_value = AsyncMock(return_value=mock_task)
            result = await executor.execute(
                "create_task",
                {
                    "title": "Tool Test",
                    "status": "todo",
                    "priority": "high",
                },
            )
        assert result["success"] is True
        assert result["task_id"] == "test-uuid-123"

    async def test_list_tasks_tool(self, user):
        from unittest.mock import AsyncMock, MagicMock, patch

        from apps.agents.services.tool_executor import ToolExecutor

        executor = ToolExecutor(user)
        mock_task = MagicMock()
        mock_task.id = "test-uuid-456"
        mock_task.title = "Listed Task"
        mock_task.description = "A task to list"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.due_date = None
        mock_task.tags = []
        mock_task.position = 0
        mock_task.created_at.isoformat.return_value = "2026-08-13T00:00:00+00:00"
        mock_task.updated_at.isoformat.return_value = "2026-08-13T00:00:00+00:00"
        with patch("apps.agents.services.tool_executor.sync_to_async") as mock_sync:
            mock_sync.return_value = AsyncMock(return_value=[mock_task])
            result = await executor.execute("list_tasks", {})
        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["id"] == "test-uuid-456"
        assert result["tasks"][0]["title"] == "Listed Task"

    async def test_unknown_tool(self, user):
        from apps.agents.services.tool_executor import ToolExecutor

        executor = ToolExecutor(user)
        result = await executor.execute("nonexistent_tool", {})
        assert result["success"] is False
