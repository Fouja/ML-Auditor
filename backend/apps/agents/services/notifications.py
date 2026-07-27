"""
Notification service — manages alert severity, priority rules, and notification delivery.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Alert severity rules ────────────────────────────────────────────

SEVERITY_RULES = {
    "critical": {
        "description": "Immediate action required",
        "notify_channels": ["email", "push", "websocket"],
        "auto_escalate_after_minutes": 15,
    },
    "high": {
        "description": "Action required within 1 hour",
        "notify_channels": ["email", "websocket"],
        "auto_escalate_after_minutes": 60,
    },
    "medium": {
        "description": "Action required within 24 hours",
        "notify_channels": ["websocket"],
        "auto_escalate_after_minutes": None,
    },
    "low": {
        "description": "Informational, no immediate action",
        "notify_channels": [],
        "auto_escalate_after_minutes": None,
    },
}


class NotificationPreferences:
    """User notification preferences manager."""

    @staticmethod
    def get_preferences(user) -> Dict[str, Any]:
        """Get user notification preferences."""
        return {
            "email_notifications": user.email_notifications,
            "push_notifications": user.push_notifications,
            "webhook_url": user.webhook_url or "",
            "alert_email_enabled": user.email_notifications,
            "alert_push_enabled": user.push_notifications,
        }

    @staticmethod
    def update_preferences(user, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Update user notification preferences."""
        if "email_notifications" in prefs:
            user.email_notifications = prefs["email_notifications"]
        if "push_notifications" in prefs:
            user.push_notifications = prefs["push_notifications"]
        if "webhook_url" in prefs:
            user.webhook_url = prefs["webhook_url"]
        user.save(update_fields=["email_notifications", "push_notifications", "webhook_url"])
        return NotificationPreferences.get_preferences(user)


class AlertRouter:
    """Routes alerts to the appropriate notification channels."""

    @staticmethod
    def determine_severity(alert_data: Dict[str, Any]) -> str:
        """Determine alert severity based on rules."""
        if alert_data.get("severity"):
            return alert_data["severity"]

        confidence = alert_data.get("confidence", 0)
        if confidence > 0.9:
            return "critical"
        elif confidence > 0.7:
            return "high"
        elif confidence > 0.4:
            return "medium"
        return "low"

    @staticmethod
    def should_notify(user, channel: str, severity: str) -> bool:
        """Check if user should be notified via channel for given severity."""
        rules = SEVERITY_RULES.get(severity, SEVERITY_RULES["low"])
        if channel not in rules["notify_channels"]:
            return False

        if channel == "email" and not user.email_notifications:
            return False
        if channel == "push" and not user.push_notifications:
            return False

        return True

    @staticmethod
    def send_notification(user, alert_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send notifications for an alert based on severity and preferences."""
        severity = AlertRouter.determine_severity(alert_data)
        sent = []

        # Email notification
        if AlertRouter.should_notify(user, "email", severity):
            try:
                AlertRouter._send_email_notification(user, alert_data, severity)
                sent.append({"channel": "email", "status": "sent"})
            except Exception as e:
                sent.append({"channel": "email", "status": "error", "error": str(e)})

        # WebSocket notification (handled by consumer)
        if AlertRouter.should_notify(user, "websocket", severity):
            sent.append({"channel": "websocket", "status": "queued"})

        return sent

    @staticmethod
    def _send_email_notification(user, alert_data: Dict, severity: str):
        """Send email notification for alert."""
        subject = f"[{severity.upper()}] {alert_data.get('title', 'Alert')}"
        body = (
            f"Severity: {severity}\n"
            f"Title: {alert_data.get('title', 'N/A')}\n"
            f"Description: {alert_data.get('description', 'N/A')}\n\n"
            f"Please review this alert in your dashboard."
        )

        if user.email_imap_host and user.email_imap_password:
            from apps.users.services.email_client import EmailClient
            client = EmailClient(
                email_address=user.email,
                password=user.email_imap_password,
                provider=user.email_provider or "custom",
                smtp_host=user.email_smtp_host,
                smtp_port=user.email_smtp_port,
                use_ssl=user.email_use_ssl,
            )
            client.send_message(to=user.email, subject=subject, body=body)
        elif user.google_access_token:
            from apps.users.services import GmailClient
            gmail = GmailClient(user)
            gmail.send_message(to=user.email, subject=subject, body=body)
