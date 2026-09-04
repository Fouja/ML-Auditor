"""
Celery tasks for integration sync jobs.
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)
llm_logger = logging.getLogger("apps.logs.llm")


@shared_task(name="apps.integrations.tasks.llm_health_check")
def llm_health_check():
    """Heartbeat: ping the NIM chat endpoint and log an LLM health metric."""
    import time

    import httpx
    from django.conf import settings

    api_key = getattr(settings, "NIM_API_KEY", "")
    base_url = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")
    if not api_key:
        try:
            from apps.integrations.models import LLMConfiguration

            cfg = LLMConfiguration.objects.filter(
                provider="nvidia", is_active=True
            ).first()
            if cfg:
                api_key = cfg.decrypted_api_key
                if cfg.model_name:
                    model = cfg.model_name
        except Exception:
            pass

    metrics_logger = logging.getLogger("apps.metrics")
    status = "error"
    latency_ms = 0
    error = ""
    try:
        start = time.monotonic()
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Reply with the single word: ok"}
                    ],
                    "max_tokens": 5,
                },
            )
            latency_ms = round((time.monotonic() - start) * 1000)
            resp.raise_for_status()
            status = "success"
    except Exception as e:
        error = str(e)[:300]
        logger.warning(f"LLM health check failed: {e}")

    llm_payload = {
        "metric": "llm_health",
        "metric_type": "llm",
        "event_type": "health_check",
        "status": status,
        "latency_ms": latency_ms,
        "model": model,
        "error": error,
    }
    metrics_logger.info(
        "llm_health",
        extra={
            "service": "llm",
            "stack": "celery",
            "metrics": llm_payload,
        },
    )
    llm_logger.info(
        "llm_health",
        extra={
            "service": "llm",
            "stack": "celery",
            "metrics": llm_payload,
        },
    )
    return {"status": status, "latency_ms": latency_ms}


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
        from apps.document_chunks.services.email_clustering import index_email_messages

        indexed = index_email_messages(user, messages, source_type="email")
        _update_connection(user, "email", success=True, items=len(messages))
        return {"synced": len(messages), "folder": folder, "indexed": indexed}
    except Exception as e:
        logger.error(f"Email sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "email", success=False, error=str(e))
        except User.DoesNotExist:
            pass
        return {"error": str(e)}


def _sync_gmail_connection(user, connection, max_results: int = 100):
    """Sync a single Gmail IntegrationConnection."""
    from apps.users.services import GmailClient
    from apps.document_chunks.services.email_clustering import index_email_messages

    gmail = GmailClient(user, connection=connection)
    messages = gmail.get_messages(max_results=max_results)
    full_emails = []
    for meta in messages:
        message_id = str(meta.get("id") or "")
        if not message_id:
            continue
        try:
            raw = gmail.get_message(message_id)
        except Exception:
            continue
        headers = {
            (h.get("name") or "").lower(): (h.get("value") or "")
            for h in raw.get("payload", {}).get("headers", [])
        }
        body = gmail.get_message_body(message_id)
        full_emails.append(
            {
                "message_id": message_id,
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "date": headers.get("date", ""),
                "body_text": body,
                "snippet": meta.get("snippet", "") or "",
                "connection_id": str(connection.id) if connection else None,
            }
        )
    indexed = index_email_messages(user, full_emails, source_type="gmail")
    return {"synced": len(messages), "indexed": indexed}


@shared_task(name="apps.integrations.tasks.sync_gmail_for_user")
def sync_gmail_for_user(user_id: int, connection_id: str = None, max_results: int = 100):
    """Sync Gmail for a single user.

    If ``connection_id`` is provided, only that account is synced. Otherwise all
    active Gmail IntegrationConnection rows for the user are synced (with a
    fallback to the legacy single-token User fields when no connections exist).
    """
    from apps.users.models import User
    from apps.integrations.models import IntegrationConnection

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": "user_not_found"}

    results = []
    try:
        if connection_id:
            connection = IntegrationConnection.objects.get(
                id=connection_id, user=user, service="gmail", is_active=True
            )
            result = _sync_gmail_connection(user, connection, max_results=max_results)
            _update_connection(user, "gmail", success=True, items=result["synced"])
            results.append({"connection_id": connection_id, **result})
        else:
            connections = IntegrationConnection.objects.filter(
                user=user, service="gmail", is_active=True
            ).order_by("-updated_at")
            if connections.exists():
                for conn in connections:
                    result = _sync_gmail_connection(user, conn, max_results=max_results)
                    _update_connection(user, "gmail", success=True, items=result["synced"])
                    results.append({"connection_id": str(conn.id), **result})
            elif user.google_access_token:
                # Legacy fallback
                result = _sync_gmail_connection(user, None, max_results=max_results)
                _update_connection(user, "gmail", success=True, items=result["synced"])
                results.append({"connection_id": None, **result})
            else:
                return {"skipped": True, "reason": "no_token"}
    except Exception as e:
        logger.error(f"Gmail sync failed for user {user_id}: {e}")
        _update_connection(user, "gmail", success=False, error=str(e))
        return {"error": str(e)}

    return {"results": results, "total_synced": sum(r["synced"] for r in results)}


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


def _sync_plaid_connection(user, connection):
    """Sync a single Plaid IntegrationConnection."""
    from apps.users.services import PlaidClient
    from .services.transaction_clustering import index_plaid_transactions

    plaid = PlaidClient(user, connection=connection)
    accounts = plaid.get_accounts()
    index_result = index_plaid_transactions(user, connection=connection)
    return {
        "accounts": len(accounts),
        "transactions_indexed": index_result.get("created", 0),
        "index_error": index_result.get("error"),
    }


@shared_task(name="apps.integrations.tasks.sync_plaid_for_user")
def sync_plaid_for_user(user_id: int, connection_id: str = None):
    """Sync Plaid accounts and recent transactions for a single user.

    If ``connection_id`` is provided, only that bank account is synced. Otherwise
    all active Plaid IntegrationConnection rows for the user are synced (with a
    fallback to the legacy single-token User fields when no connections exist).
    """
    from apps.users.models import User
    from apps.integrations.models import IntegrationConnection

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": "user_not_found"}

    results = []
    try:
        if connection_id:
            connection = IntegrationConnection.objects.get(
                id=connection_id, user=user, service="plaid", is_active=True
            )
            result = _sync_plaid_connection(user, connection)
            _update_connection(user, "plaid", success=True, items=result["transactions_indexed"])
            results.append({"connection_id": connection_id, **result})
        else:
            connections = IntegrationConnection.objects.filter(
                user=user, service="plaid", is_active=True
            ).order_by("-updated_at")
            if connections.exists():
                for conn in connections:
                    result = _sync_plaid_connection(user, conn)
                    _update_connection(
                        user, "plaid", success=True, items=result["transactions_indexed"]
                    )
                    results.append({"connection_id": str(conn.id), **result})
            elif user.plaid_access_token:
                # Legacy fallback
                result = _sync_plaid_connection(user, None)
                _update_connection(user, "plaid", success=True, items=result["transactions_indexed"])
                results.append({"connection_id": None, **result})
            else:
                return {"skipped": True, "reason": "no_token"}
    except Exception as e:
        logger.error(f"Plaid sync failed for user {user_id}: {e}")
        _update_connection(user, "plaid", success=False, error=str(e))
        return {"error": str(e)}

    return {
        "results": results,
        "total_accounts": sum(r["accounts"] for r in results),
        "total_transactions_indexed": sum(r["transactions_indexed"] for r in results),
    }


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


@shared_task(name="apps.integrations.tasks.sync_jira_for_user")
def sync_jira_for_user(user_id: int, project_key: str = None, max_results: int = 50):
    """Sync Jira issues into RAG data store for a single user."""
    from apps.document_chunks.models import DocumentChunk
    from apps.data_streams.models import DataStream
    from apps.users.models import User
    from apps.users.services.jira_client import JiraClient

    try:
        user = User.objects.get(id=user_id)
        if not user.jira_site_url or not user.jira_api_token:
            return {"skipped": True, "reason": "no_config"}

        client = JiraClient(
            site_url=user.jira_site_url,
            email=user.jira_email,
            api_token=user.jira_api_token,
        )
        issues = client.get_issues(project_key=project_key, max_results=max_results)

        stream, _ = DataStream.objects.get_or_create(
            user=user,
            source_type="jira",
            defaults={"payload": {"project_key": project_key or "all"}},
        )

        for issue in issues:
            text = (
                f"Issue: {issue['key']}\n"
                f"Summary: {issue['summary']}\n"
                f"Status: {issue['status']}\n"
                f"Priority: {issue['priority']}\n"
                f"Type: {issue['issue_type']}\n"
                f"Project: {issue['project_name']}\n"
                f"Assignee: {issue['assignee_display']}\n"
                f"Labels: {', '.join(issue['labels'])}\n"
            )
            if issue.get("description"):
                text += f"Description: {issue['description']}\n"
            if issue.get("due_date"):
                text += f"Due: {issue['due_date']}\n"

            from apps.document_chunks.services.embedding_generation import _generate_embedding_sync

            chunk = DocumentChunk.objects.create(
                stream=stream,
                content=text,
                cluster_category="jira",
                embedding=_generate_embedding_sync(text),
                metadata={
                    "issue_key": issue["key"],
                    "issue_url": issue["url"],
                    "issue_type": issue["issue_type"],
                    "status": issue["status"],
                    "priority": issue["priority"],
                    "project": issue["project_name"],
                    "updated": issue["updated"],
                },
            )

        _update_connection(user, "jira", success=True, items=len(issues))
        return {"synced": len(issues)}
    except Exception as e:
        logger.error(f"Jira sync failed for user {user_id}: {e}")
        try:
            user = User.objects.get(id=user_id)
            _update_connection(user, "jira", success=False, error=str(e))
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


def test_api_key_integration(user, key):
    """Test an ApiKeyIntegration record and return a status dict.

    This performs a lightweight validation against the upstream service
    without running a full sync.
    """
    service = key.service
    api_key = key.decrypted_api_key
    api_secret = key.decrypted_api_secret

    if not api_key:
        return {"success": False, "status": "error", "error": "API key is empty"}

    try:
        if service == "plaid":
            from apps.users.services.plaid_client import PlaidClient

            client = PlaidClient.with_credentials(
                client_id=api_key,
                secret=api_secret,
                environment=key.extra_data.get("environment", "sandbox"),
            )
            return {"success": True, "status": "active"} if client.health_check() else {"success": False, "status": "error", "error": "Plaid health check failed"}

        if service in ("gmail", "google_calendar"):
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError

            creds = Credentials(token=api_key)
            service_name = "gmail" if service == "gmail" else "calendar"
            version = "v1"
            build(service_name, version, credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()
            return {"success": True, "status": "active"}

        if service == "jira":
            import requests
            from requests.auth import HTTPBasicAuth

            site_url = key.extra_data.get("site_url", "")
            email = key.extra_data.get("email", "")
            if not site_url or not email:
                return {"success": False, "status": "error", "error": "Jira requires site_url and email in extra data"}
            url = site_url.rstrip("/") + "/rest/api/3/myself"
            resp = requests.get(url, auth=HTTPBasicAuth(email, api_key), timeout=15)
            resp.raise_for_status()
            return {"success": True, "status": "active"}

        if service == "canva":
            import requests

            resp = requests.get(
                "https://api.canva.com/rest/v1/designs",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            if resp.status_code in (200, 401):
                # 401 usually means valid token but insufficient scopes; treat as reachable.
                return {"success": True, "status": "active"}
            resp.raise_for_status()
            return {"success": True, "status": "active"}

        if service in ("openai", "anthropic", "nvidia"):
            import requests

            provider_endpoints = {
                "openai": "https://api.openai.com/v1/models",
                "anthropic": "https://api.anthropic.com/v1/models",
                "nvidia": "https://integrate.api.nvidia.com/v1/models",
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            if service == "anthropic":
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            resp = requests.get(provider_endpoints[service], headers=headers, timeout=15)
            resp.raise_for_status()
            return {"success": True, "status": "active"}

        if service == "custom":
            endpoint = key.extra_data.get("endpoint", "")
            if not endpoint:
                return {"success": False, "status": "error", "error": "Custom API requires an endpoint in extra data"}
            import requests

            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(endpoint, headers=headers, timeout=15)
            resp.raise_for_status()
            return {"success": True, "status": "active"}

        return {"success": False, "status": "error", "error": f"Testing not implemented for {service}"}
    except HttpError as exc:
        return {"success": False, "status": "error", "error": f"Google API error: {exc.reason or exc.status_code}"}
    except Exception as exc:
        return {"success": False, "status": "error", "error": str(exc)}
