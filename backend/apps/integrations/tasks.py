"""
Celery tasks for integration sync jobs.
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task

logger = logging.getLogger(__name__)


def _update_connection(user, service, success, items=0, error=""):
    """Update IntegrationConnection after a sync run."""
    from .models import IntegrationConnection, SyncLog

    conn, _ = IntegrationConnection.objects.get_or_create(user=user, service=service)

    SyncLog.objects.create(
        connection=conn,
        finished_at=datetime.utcnow(),
        success=success,
        items_synced=items,
        error_message=error,
    )

    conn.last_synced = datetime.utcnow()
    conn.items_synced += items if success else 0
    conn.status = "active" if success else "error"
    conn.last_error = error
    conn.save(update_fields=["last_synced", "items_synced", "status", "last_error"])


@shared_task(name="apps.integrations.tasks.sync_email_for_user")
def sync_email_for_user(user_id: int, folder: str = "INBOX", max_results: int = 100):
    """Sync email via IMAP for a single user."""
    from apps.users.models import User
    from apps.users.services.email_client import EmailClient

    try:
        user = User.objects.get(id=user_id)
        if not user.email_imap_host or not user.email_imap_password:
            return {"skipped": True, "reason": "no_config"}

        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            imap_host=user.email_imap_host,
            imap_port=user.email_imap_port,
            use_ssl=user.email_use_ssl,
        )
        messages = client.get_messages(folder=folder, limit=max_results)
        _update_connection(user, "email", success=True, items=len(messages))
        return {"synced": len(messages), "folder": folder}
    except Exception as e:
        logger.error(f"Email sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "email", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


@shared_task(name="apps.integrations.tasks.sync_gmail_for_user")
def sync_gmail_for_user(user_id: int, max_results: int = 100):
    """Sync Gmail for a single user."""
    from apps.users.models import User
    from apps.users.services import GmailClient

    try:
        user = User.objects.get(id=user_id)
        if not user.google_access_token:
            return {"skipped": True, "reason": "no_token"}

        gmail = GmailClient(user)
        messages = gmail.get_messages(max_results=max_results)
        _update_connection(user, "gmail", success=True, items=len(messages))
        return {"synced": len(messages)}
    except Exception as e:
        logger.error(f"Gmail sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "gmail", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


@shared_task(name="apps.integrations.tasks.sync_calendar_for_user")
def sync_calendar_for_user(user_id: int, hours: int = 168):
    """Sync Google Calendar for a single user."""
    from apps.users.models import User
    from apps.users.services import CalendarClient

    try:
        user = User.objects.get(id=user_id)
        if not user.google_access_token:
            return {"skipped": True, "reason": "no_token"}

        cal = CalendarClient(user)
        now = datetime.utcnow()
        events = cal.get_events(time_min=now, time_max=now + timedelta(hours=hours))
        _update_connection(user, "google_calendar", success=True, items=len(events))
        return {"synced": len(events)}
    except Exception as e:
        logger.error(f"Calendar sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "google_calendar", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


@shared_task(name="apps.integrations.tasks.sync_plaid_for_user")
def sync_plaid_for_user(user_id: int):
    """Sync Plaid accounts and recent transactions for a single user."""
    from apps.users.models import User
    from apps.users.services import PlaidClient

    try:
        user = User.objects.get(id=user_id)
        if not user.plaid_access_token:
            return {"skipped": True, "reason": "no_token"}

        plaid = PlaidClient(user)
        accounts = plaid.get_accounts()
        end = datetime.now()
        start = end - timedelta(days=30)
        transactions = plaid.get_transactions(start_date=start, end_date=end)
        _update_connection(user, "plaid", success=True, items=len(transactions))
        return {"accounts": len(accounts), "transactions": len(transactions)}
    except Exception as e:
        logger.error(f"Plaid sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "plaid", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


@shared_task(name="apps.integrations.tasks.sync_canva_for_user")
def sync_canva_for_user(user_id: int):
    """Sync Canva designs for a single user."""
    from apps.users.models import User
    from apps.users.services.canva_client import CanvaClient

    try:
        user = User.objects.get(id=user_id)
        if not user.canva_access_token:
            return {"skipped": True, "reason": "no_token"}

        client = CanvaClient(user.canva_access_token)
        designs = client.get_designs(limit=50)
        _update_connection(user, "canva", success=True, items=len(designs))
        return {"synced": len(designs)}
    except Exception as e:
        logger.error(f"Canva sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "canva", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


@shared_task(name="apps.integrations.tasks.sync_kijiji_for_user")
def sync_kijiji_for_user(user_id: int):
    """Sync Kijiji messages for a single user."""
    from apps.users.models import User
    from apps.users.services import KijijiScraperService

    try:
        user = User.objects.get(id=user_id)
        scraper = KijijiScraperService(user=user)
        messages = scraper.get_messages(limit=50)
        _update_connection(user, "kijiji", success=True, items=len(messages))
        return {"synced": len(messages)}
    except Exception as e:
        logger.error(f"Kijiji sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "kijiji", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}
