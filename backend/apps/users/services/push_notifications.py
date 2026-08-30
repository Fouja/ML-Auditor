"""Push notification service using Expo Push API."""

import logging
from typing import List

import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification(tokens: List[str], title: str, body: str, data: dict = None):
    """Send a push notification to a list of Expo push tokens."""
    if not tokens:
        return {"success": False, "error": "No tokens provided"}

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
            "priority": "high",
        }
        for token in tokens
    ]

    try:
        response = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return {"success": False, "error": str(e)}


def notify_user(user, title: str, body: str, data: dict = None):
    """Send a push notification to all active tokens for a user."""
    from apps.users.models import PushToken

    tokens = list(
        PushToken.objects.filter(user=user, is_active=True)
        .values_list("token", flat=True)
        .distinct()
    )
    return send_push_notification(tokens, title, body, data)
