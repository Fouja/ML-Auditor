"""
WebSocket URL routing for ML-Auditor.

The alerts app owns its consumers, so it owns the routes too.
"""

from django.urls import re_path

from .consumers import (
    AlertsConsumer,
    AnalyticsConsumer,
    NotificationsConsumer,
)

websocket_urlpatterns = [
    re_path(
        r"ws/alerts/$",
        AlertsConsumer.as_asgi(),
    ),
    re_path(
        r"ws/analytics/$",
        AnalyticsConsumer.as_asgi(),
    ),
    re_path(
        r"ws/notifications/$",
        NotificationsConsumer.as_asgi(),
    ),
]
