"""
Integration signal receivers.

Whenever an IntegrationLog or SyncLog is created, mirror it as a structured
JSON log line so it can be searched alongside the rest of the project's logs
in Kibana.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import IntegrationLog, SyncLog

integration_logger = logging.getLogger("apps.logs.integration")


@receiver(post_save, sender=IntegrationLog)
def log_integration_event(sender, instance: IntegrationLog, created: bool, **kwargs):
    if not created:
        return

    level = instance.level
    log_level = {
        "success": logging.INFO,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }.get(level, logging.INFO)

    integration_logger.log(
        log_level,
        instance.message,
        extra={
            "service": "integration",
            "stack": "django",
            "metrics": {
                "integration_service": instance.service,
                "event_type": "integration_log",
                "level": level,
                "user_id": str(getattr(instance.user, "id", "")),
                "metadata": instance.metadata,
            },
        },
    )


@receiver(post_save, sender=SyncLog)
def log_sync_event(sender, instance: SyncLog, created: bool, **kwargs):
    if not created:
        return

    connection = instance.connection
    service = connection.service if connection else "unknown"
    user_id = str(getattr(connection, "user_id", "")) if connection else ""

    log_level = logging.INFO if instance.success else logging.ERROR
    integration_logger.log(
        log_level,
        f"{service} sync {'succeeded' if instance.success else 'failed'}",
        extra={
            "service": "integration",
            "stack": "django",
            "metrics": {
                "integration_service": service,
                "event_type": "sync",
                "success": instance.success,
                "items_synced": instance.items_synced,
                "user_id": user_id,
                "error_message": instance.error_message,
            },
        },
    )
