"""
Integration API endpoints for external services.
Email (IMAP/SMTP + Gmail), Calendar, Plaid, Canva, Kijiji.
"""

from django.conf import settings
from ninja import Query, Router

from ninja import Schema

from .schemas import (
    ApiKeyCreateSchema,
    ApiKeyResponseSchema,
    ApiKeyTestResponseSchema,
    ApiKeyUpdateSchema,
    CalendarEventCreateSchema,
    CanvaCompetitorSchema,
    CanvaSearchSchema,
    EmailSendSchema,
    IMAPConfigSchema,
    IMAPSendSchema,
    IntegrationAccountCreateSchema,
    IntegrationAccountUpdateSchema,
    IntegrationLogResponseSchema,
    JiraConfigureSchema,
    JiraSyncSchema,
    KijijiSearchSchema,
    PlaidApiKeySchema,
    PlaidExchangeSchema,
)


class WebToolsPreferenceSchema(Schema):
    enabled: bool = False

router = Router()


# ─── Connection status ───────────────────────────────────────────────


def _account_list(user, service: str):
    from .models import IntegrationConnection

    return [
        {
            "id": str(conn.id),
            "label": conn.account_label,
            "service": conn.service,
            "status": conn.status,
            "is_active": conn.is_active,
            "last_synced": conn.last_synced.isoformat() if conn.last_synced else None,
            "items_synced": conn.items_synced,
        }
        for conn in IntegrationConnection.objects.filter(user=user, service=service, is_active=True)
    ]


def _has_api_key(user, service: str) -> bool:
    from .models import ApiKeyIntegration

    return ApiKeyIntegration.objects.filter(user=user, service=service, is_active=True).exists()


@router.get("/status")
def integration_status(request):
    """Get status of all integrations, including per-account lists for Gmail/Plaid and API keys."""
    user = request.auth
    gmail_accounts = _account_list(user, "gmail")
    plaid_accounts = _account_list(user, "plaid")
    return {
        "email": {
            "imap_connected": bool(getattr(user, "email_verified", False)),
            "gmail_connected": bool(gmail_accounts) or bool(user.google_access_token),
            "provider": user.email_provider or "custom",
        },
        "gmail": {
            "connected": bool(gmail_accounts) or bool(user.google_access_token) or _has_api_key(user, "gmail"),
            "accounts": gmail_accounts,
        },
        "calendar": {
            "connected": bool(user.google_access_token) or _has_api_key(user, "google_calendar"),
        },
        "plaid": {
            "connected": bool(plaid_accounts) or bool(getattr(user, "plaid_verified", False)) or _has_api_key(user, "plaid"),
            "accounts": plaid_accounts,
        },
        "canva": {
            "connected": bool(user.canva_access_token) or _has_api_key(user, "canva"),
        },
        "kijiji": {"connected": True},
        "jira": {
            "connected": bool(user.jira_site_url) or _jira_oauth_connected(user) or _has_api_key(user, "jira"),
        },
        "web_tools": {"enabled": bool(getattr(user, "web_tools_enabled", False))},
        "mock_data": {"enabled": bool(getattr(user, "mock_data_enabled", False))},
    }


@router.get("/web-tools/preference")
def web_tools_preference(request):
    user = request.auth
    return {"enabled": bool(getattr(user, "web_tools_enabled", False))}


@router.post("/web-tools/preference")
def set_web_tools_preference(request, payload: WebToolsPreferenceSchema):
    user = request.auth
    user.web_tools_enabled = bool(payload.enabled)
    user.save(update_fields=["web_tools_enabled"])
    return {"enabled": user.web_tools_enabled}


# ─── Multi-account connections (Gmail / Plaid) ────────────────────────


@router.get("/accounts")
def list_accounts(request, service: str = ""):
    """List active integration accounts for the current user."""
    from .models import IntegrationConnection

    user = request.auth
    qs = IntegrationConnection.objects.filter(user=user, is_active=True)
    if service:
        qs = qs.filter(service=service)
    return {
        "accounts": [
            {
                "id": str(conn.id),
                "service": conn.service,
                "label": conn.account_label,
                "status": conn.status,
                "is_active": conn.is_active,
                "last_synced": conn.last_synced.isoformat() if conn.last_synced else None,
                "items_synced": conn.items_synced,
                "extra_data": conn.extra_data,
            }
            for conn in qs.order_by("service", "account_label")
        ],
        "count": qs.count(),
    }


@router.post("/accounts")
def create_account(request, payload: IntegrationAccountCreateSchema):
    """Manually add an integration account (mainly for testing/service accounts)."""
    from .models import IntegrationConnection

    user = request.auth
    conn, created = IntegrationConnection.objects.get_or_create(
        user=user,
        service=payload.service,
        account_label=payload.account_label,
        defaults={
            "access_token": payload.access_token or "",
            "refresh_token": payload.refresh_token or "",
            "extra_data": payload.extra_data or {},
            "status": "active",
            "is_active": True,
        },
    )
    if not created:
        if payload.access_token is not None:
            conn.access_token = payload.access_token
        if payload.refresh_token is not None:
            conn.refresh_token = payload.refresh_token
        if payload.extra_data is not None:
            conn.extra_data = payload.extra_data
        conn.is_active = True
        conn.save(update_fields=["access_token", "refresh_token", "extra_data", "is_active"])
    return {
        "id": str(conn.id),
        "service": conn.service,
        "label": conn.account_label,
        "created": created,
    }


@router.patch("/accounts/{account_id}")
def update_account(request, account_id: str, payload: IntegrationAccountUpdateSchema):
    """Update an integration account label/active state."""
    from .models import IntegrationConnection

    user = request.auth
    conn = IntegrationConnection.objects.get(id=account_id, user=user)
    if payload.account_label is not None:
        conn.account_label = payload.account_label
    if payload.is_active is not None:
        conn.is_active = payload.is_active
    if payload.extra_data is not None:
        conn.extra_data = payload.extra_data
    conn.save(update_fields=["account_label", "is_active", "extra_data"])
    return {
        "id": str(conn.id),
        "service": conn.service,
        "label": conn.account_label,
        "is_active": conn.is_active,
    }


@router.delete("/accounts/{account_id}")
def delete_account(request, account_id: str):
    """Disconnect/delete an integration account."""
    from .models import IntegrationConnection

    user = request.auth
    conn = IntegrationConnection.objects.get(id=account_id, user=user)
    conn.is_active = False
    conn.status = "disconnected"
    conn.save(update_fields=["is_active", "status"])
    return {"success": True, "id": account_id}


@router.post("/accounts/{account_id}/sync")
def sync_account(request, account_id: str):
    """Sync a single integration account on demand."""
    from .models import IntegrationConnection

    user = request.auth
    conn = IntegrationConnection.objects.get(id=account_id, user=user, is_active=True)
    if conn.service == "gmail":
        from .tasks import sync_gmail_for_user

        result = sync_gmail_for_user.delay(str(user.id), connection_id=str(conn.id))
        return {"success": True, "task_id": result.id, "service": "gmail"}
    if conn.service == "plaid":
        from .tasks import sync_plaid_for_user

        result = sync_plaid_for_user.delay(str(user.id), connection_id=str(conn.id))
        return {"success": True, "task_id": result.id, "service": "plaid"}
    return {"success": False, "error": f"Sync not implemented for {conn.service}"}


# ─── Mock data (demo content) ───────────────────────────────────────


@router.get("/mock/status")
def mock_data_status(request):
    """Get the user's mock-data activation status."""
    from .services.mock_data import mock_data_status

    return mock_data_status(request.auth)


@router.post("/mock")
def set_mock_data(request, payload: WebToolsPreferenceSchema):
    """Activate or deactivate mock data for the user."""
    from .services.mock_data import activate_mock_data, deactivate_mock_data

    user = request.auth
    if payload.enabled:
        return activate_mock_data(user)
    return deactivate_mock_data(user)


# ─── Generic IMAP/SMTP Email ────────────────────────────────────────


@router.post("/email/configure")
def email_configure(request, payload: IMAPConfigSchema):
    """Configure IMAP/SMTP settings for any email provider.

    Saves the config AND tests the connexion live. email_verified is
    flipped to True only if the IMAP login actually succeeds — so the
    UI's "connected" badge reflects reality, not just presence of fields.
    """
    from apps.users.services.email_client import EmailClient

    user = request.auth
    user.email_provider = payload.provider
    user.email_imap_host = payload.imap_host
    user.email_imap_port = payload.imap_port
    user.email_smtp_host = payload.smtp_host
    user.email_smtp_port = payload.smtp_port
    user.email_imap_password = payload.password
    user.email_use_ssl = payload.use_ssl
    user.email_verified = False
    user.save(
        update_fields=[
            "email_provider",
            "email_imap_host",
            "email_imap_port",
            "email_smtp_host",
            "email_smtp_port",
            "email_imap_password",
            "email_use_ssl",
            "email_verified",
        ]
    )

    test_result = {"success": False, "error": "no password provided"}
    if payload.password:
        client = EmailClient(
            email_address=user.email,
            password=payload.password,
            provider=payload.provider or "custom",
            imap_host=payload.imap_host,
            imap_port=payload.imap_port,
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            use_ssl=payload.use_ssl,
        )
        test_result = client.test_connection()

    user.email_verified = bool(test_result.get("success"))
    user.save(update_fields=["email_verified"])

    return {
        "success": test_result.get("success", False),
        "verified": user.email_verified,
        "error": test_result.get("error") if not test_result.get("success") else None,
    }


@router.get("/email/status")
def email_status(request):
    """Check email IMAP/SMTP connection status.

    Returns connected=True ONLY when the credentials have been verified
    (user.email_verified flag). Having a saved host+password does NOT
    mean the connexion actually works — we test login when the user
    saves their config and flip email_verified accordingly.
    """
    user = request.auth
    configured = bool(user.email_imap_host and user.email_imap_password)
    verified = bool(getattr(user, "email_verified", False))
    connected = configured and verified
    return {
        "connected": connected,
        "configured": configured,
        "verified": verified,
        "provider": user.email_provider or "custom",
        "imap_host": user.email_imap_host or "",
    }


@router.get("/email/test")
def email_test(request):
    """Test IMAP connection."""
    from apps.users.services.email_client import EmailClient

    user = request.auth
    if not user.email_imap_host or not user.email_imap_password:
        return {
            "success": False,
            "error": "Email not configured. Please configure email first.",
        }

    client = EmailClient(
        email_address=user.email,
        password=user.email_imap_password,
        provider=user.email_provider or "custom",
        imap_host=user.email_imap_host,
        imap_port=user.email_imap_port,
        smtp_host=user.email_smtp_host,
        smtp_port=user.email_smtp_port,
        use_ssl=user.email_use_ssl,
    )
    return client.test_connection()


@router.get("/email/folders")
def email_folders(request):
    """List IMAP folders."""
    from apps.users.services.email_client import EmailClient

    user = request.auth
    if not user.email_imap_host or not user.email_imap_password:
        return {"folders": [], "error": "Email not configured"}

    client = EmailClient(
        email_address=user.email,
        password=user.email_imap_password,
        provider=user.email_provider or "custom",
        imap_host=user.email_imap_host,
        imap_port=user.email_imap_port,
        use_ssl=user.email_use_ssl,
    )
    try:
        folders = client.get_folders()
        return {"folders": folders}
    except Exception as e:
        return {"folders": [], "error": f"Failed to list folders: {str(e)}"}


@router.get("/email/sync")
def email_sync(request, folder: str = "INBOX", limit: int = Query(50)):
    """Sync emails from IMAP (any provider)."""
    from apps.users.services.email_client import EmailClient

    user = request.auth
    if not user.email_imap_host or not user.email_imap_password:
        return {
            "messages": [],
            "count": 0,
            "folder": folder,
            "error": "Email not configured",
        }

    try:
        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            imap_host=user.email_imap_host,
            imap_port=user.email_imap_port,
            use_ssl=user.email_use_ssl,
        )
        messages = client.get_messages(folder=folder, limit=limit)
        return {
            "messages": messages,
            "count": len(messages),
            "folder": folder,
        }
    except ConnectionRefusedError:
        return {
            "messages": [],
            "count": 0,
            "folder": folder,
            "error": "Could not connect to email server. Check your IMAP host settings.",
        }
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Email sync error: {e}")
        return {
            "messages": [],
            "count": 0,
            "folder": folder,
            "error": f"Email sync failed: {str(e)}",
        }


@router.get("/email/search")
def email_search(request, q: str = "", folder: str = "INBOX", limit: int = Query(50)):
    """Search emails via IMAP."""
    from apps.users.services.email_client import EmailClient

    user = request.auth
    if not user.email_imap_host or not user.email_imap_password:
        return {"messages": [], "count": 0, "error": "Email not configured"}

    try:
        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            imap_host=user.email_imap_host,
            imap_port=user.email_imap_port,
            use_ssl=user.email_use_ssl,
        )
        messages = client.search_messages(query=q, folder=folder, limit=limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Email search error: {e}")
        return {"messages": [], "count": 0, "error": f"Email search failed: {str(e)}"}


@router.post("/email/send")
def email_send(request, payload: IMAPSendSchema):
    """Send email via SMTP (any provider)."""
    from apps.users.services.email_client import EmailClient

    user = request.auth
    if not user.email_smtp_host or not user.email_imap_password:
        return {
            "success": False,
            "error": "Email not configured. Please configure SMTP settings first.",
        }

    try:
        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            smtp_host=user.email_smtp_host,
            smtp_port=user.email_smtp_port,
            use_ssl=user.email_use_ssl,
        )
        client.send_message(
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
            cc=payload.cc,
            html=payload.html,
        )
        return {"success": True}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Email send error: {e}")
        return {"success": False, "error": f"Failed to send email: {str(e)}"}


# ─── Gmail (Google API) ─────────────────────────────────────────────


@router.get("/gmail/status")
def gmail_status(request):
    from .models import IntegrationConnection

    user = request.auth
    active = IntegrationConnection.objects.filter(
        user=user, service="gmail", is_active=True
    ).exists()
    return {
        "connected": active or bool(user.google_access_token),
        "has_refresh_token": bool(user.google_refresh_token),
        "accounts": _account_list(user, "gmail"),
    }


@router.get("/gmail/sync")
def gmail_sync(request, max_results: int = Query(50), connection_id: str = ""):
    from apps.users.services import GmailClient
    from .models import IntegrationConnection

    user = request.auth
    connections = IntegrationConnection.objects.filter(
        user=user, service="gmail", is_active=True
    )
    if not connections.exists() and not user.google_access_token:
        return {"messages": [], "count": 0, "error": "Gmail not connected"}

    if connection_id:
        connections = connections.filter(id=connection_id)

    all_messages = []
    errors = []
    for conn in connections:
        try:
            gmail = GmailClient(user, connection=conn)
            messages = gmail.get_messages(max_results=max_results)
            for msg in messages[:max_results]:
                full = gmail.get_message(msg["id"])
                headers = full.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")
                all_messages.append(
                    {
                        "id": msg["id"],
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "snippet": full.get("snippet", ""),
                        "connection_id": str(conn.id),
                        "connection_label": conn.account_label,
                    }
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Gmail sync error for {conn.id}: {e}")
            errors.append(str(e))

    if not connections.exists() and user.google_access_token:
        # Legacy fallback
        try:
            gmail = GmailClient(user)
            messages = gmail.get_messages(max_results=max_results)
            for msg in messages[:max_results]:
                full = gmail.get_message(msg["id"])
                headers = full.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")
                all_messages.append(
                    {
                        "id": msg["id"],
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "snippet": full.get("snippet", ""),
                    }
                )
        except Exception as e:
            errors.append(str(e))

    return {
        "messages": all_messages,
        "count": len(all_messages),
        "errors": errors if errors else None,
    }


@router.post("/gmail/send")
def gmail_send(request, payload: EmailSendSchema):
    from apps.users.services import GmailClient
    from .models import IntegrationConnection

    user = request.auth
    connection = (
        IntegrationConnection.objects.filter(
            user=user, service="gmail", is_active=True
        ).first()
    )
    if not connection and not user.google_access_token:
        return {"success": False, "error": "Gmail not connected"}

    try:
        gmail = GmailClient(user, connection=connection)
        result = gmail.send_message(
            to=payload.to, subject=payload.subject, body=payload.body, cc=payload.cc
        )
        return {"success": True, "message_id": result.get("id")}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Gmail send error: {e}")
        return {"success": False, "error": f"Failed to send email: {str(e)}"}


@router.post("/gmail/sync-clusters")
def gmail_sync_clusters(request, connection_id: str = ""):
    """Synchronously fetch Gmail messages and index them into the RAG store.

    If ``connection_id`` is provided, only that account is synced. Otherwise all
    active Gmail connections are synced.
    """
    from .models import IntegrationConnection

    user = request.auth
    has_connection = IntegrationConnection.objects.filter(
        user=user, service="gmail", is_active=True
    ).exists()
    if not has_connection and not user.google_access_token:
        return {"success": False, "error": "Gmail not connected"}
    try:
        from .tasks import sync_gmail_for_user

        kwargs = {"user_id": str(user.id), "max_results": 100}
        if connection_id:
            kwargs["connection_id"] = connection_id
        result = sync_gmail_for_user.apply(kwargs=kwargs)
        return {"success": True, **(result.result or {})}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Gmail sync-clusters error: {e}")
        return {"success": False, "error": str(e)}


# ─── Google Calendar ─────────────────────────────────────────────────


@router.get("/calendar/status")
def calendar_status(request):
    user = request.auth
    return {"connected": bool(user.google_access_token)}


@router.get("/calendar/events")
def calendar_events(request, hours: int = Query(168)):
    from datetime import datetime, timedelta

    from apps.users.services import CalendarClient

    user = request.auth
    if not user.google_access_token:
        return {"events": [], "count": 0, "error": "Calendar not connected"}

    try:
        cal = CalendarClient(user)
        now = datetime.utcnow()
        events = cal.get_events(time_min=now, time_max=now + timedelta(hours=hours))
        results = []
        for ev in events:
            start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
            end = ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date"))
            results.append(
                {
                    "id": ev.get("id"),
                    "summary": ev.get("summary", ""),
                    "description": ev.get("description", ""),
                    "location": ev.get("location", ""),
                    "start": start,
                    "end": end,
                    "attendees": [a.get("email") for a in ev.get("attendees", [])],
                    "html_link": ev.get("htmlLink"),
                }
            )
        return {"events": results, "count": len(results)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Calendar events error: {e}")
        return {"events": [], "count": 0, "error": f"Failed to fetch events: {str(e)}"}


@router.post("/calendar/events")
def create_calendar_event(request, payload: CalendarEventCreateSchema):
    from datetime import datetime

    from apps.users.services import CalendarClient

    user = request.auth
    if not user.google_access_token:
        return {"success": False, "error": "Calendar not connected"}

    try:
        cal = CalendarClient(user)
        event = cal.create_event(
            summary=payload.summary,
            start_time=datetime.fromisoformat(payload.start_time),
            end_time=datetime.fromisoformat(payload.end_time),
            description=payload.description,
            location=payload.location,
            attendees=payload.attendees,
        )
        return {"success": True, "event_id": event.get("id")}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Create calendar event error: {e}")
        return {"success": False, "error": f"Failed to create event: {str(e)}"}


# ─── Plaid ───────────────────────────────────────────────────────────


@router.get("/plaid/status")
def plaid_status(request):
    """Plaid connexion status — verified = access token has actually been
    validated against Plaid, not merely present in the DB.
    """
    from .models import IntegrationConnection

    user = request.auth
    active = IntegrationConnection.objects.filter(
        user=user, service="plaid", is_active=True
    ).exists()
    return {
        "connected": active or bool(getattr(user, "plaid_verified", False)),
        "configured": active or bool(user.plaid_access_token),
        "accounts": _account_list(user, "plaid"),
    }


@router.get("/plaid/mode")
def plaid_mode(request):
    """Plaid environment info. Real bank logins (e.g. Scotia) only work in
    development/production; in sandbox Plaid Link accepts only test creds.
    """
    from apps.users.services import PlaidClient

    plaid = PlaidClient(request.auth)
    return {
        "mode": plaid.env,
        "real_bank_supported": plaid.env != "sandbox",
        "configured": bool(plaid.client_id and plaid.secret),
    }


@router.get("/plaid/link-token")
def plaid_link_token(request):
    from apps.users.services import PlaidClient

    user = request.auth
    try:
        creds = _get_user_plaid_credentials(user)
        if creds:
            plaid = PlaidClient.with_credentials(
                client_id=creds["client_id"],
                secret=creds["secret"],
                environment=creds["environment"],
            )
        else:
            plaid = PlaidClient(user)
        result = plaid.create_link_token(user_id=str(user.id))
        link_token = result.get("link_token")
        if not link_token:
            missing = []
            if not plaid.client_id:
                missing.append("PLAID_CLIENT_ID")
            if not plaid.secret:
                missing.append("PLAID_SECRET")
            hint = (
                f"Plaid credentials not configured. Set {', '.join(missing)} "
                "in your .env (sandbox keys from https://dashboard.plaid.com/sandbox/keys)."
                if missing
                else f"Plaid rejected the request: {result}"
            )
            return {"link_token": None, "error": hint, "mode": plaid.env}
        return {
            "link_token": link_token,
            "expiration": result.get("expiration"),
            "mode": plaid.env,
            # Real bank logins (e.g. Scotia) only work in development/production.
            # In sandbox, Plaid Link accepts only the fake test credentials.
            "real_bank_supported": plaid.env != "sandbox",
        }
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid link token error: {e}")
        msg = str(e)
        hint = msg
        if "Bad Request" in msg or "400" in msg:
            hint = (
                "Plaid rejected the link-token request. The most common cause is "
                "missing PLAID_CLIENT_ID / PLAID_SECRET env vars on the backend "
                "container. Get sandbox keys at "
                "https://dashboard.plaid.com/sandbox/keys and restart the backend."
            )
        return {"link_token": None, "error": f"Failed to create link token: {hint}", "mode": plaid.env}


@router.post("/plaid/exchange")
def plaid_exchange(request, payload: PlaidExchangeSchema):
    from apps.users.services import PlaidClient

    user = request.auth
    try:
        creds = _get_user_plaid_credentials(user)
        if creds:
            plaid = PlaidClient.with_credentials(
                client_id=creds["client_id"],
                secret=creds["secret"],
                environment=creds["environment"],
            )
        else:
            plaid = PlaidClient(user)
        result = plaid.exchange_public_token(payload.public_token)
        access_token = result.get("access_token")
        if access_token:
            user.plaid_access_token = access_token
            user.plaid_verified = True
            user.save(update_fields=["plaid_access_token", "plaid_verified"])

            # Store as a multi-account connection.
            from .models import IntegrationConnection

            label = payload.account_label or "Plaid"
            conn, _ = IntegrationConnection.objects.get_or_create(
                user=user,
                service="plaid",
                account_label=label,
                defaults={
                    "access_token": access_token,
                    "status": "active",
                    "is_active": True,
                },
            )
            conn.access_token = access_token
            conn.is_active = True
            conn.save(update_fields=["access_token", "is_active"])

            try:
                from .tasks import sync_plaid_for_user

                sync_plaid_for_user.delay(str(user.id))
            except Exception:
                pass
            try:
                from .services.transaction_clustering import index_plaid_transactions

                index_plaid_transactions(user, connection=conn)
            except Exception as idx_err:
                import logging

                logging.getLogger(__name__).warning(f"Plaid index after exchange: {idx_err}")
        return {"success": True, "connection_id": str(conn.id) if access_token else None}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid exchange error: {e}")
        return {"success": False, "error": f"Token exchange failed: {str(e)}"}


def _get_user_plaid_credentials(user):
    """Return user-provided Plaid client_id/secret if available."""
    from .models import ApiKeyIntegration

    key = ApiKeyIntegration.objects.filter(user=user, service="plaid", is_active=True).first()
    if not key:
        return None
    return {
        "client_id": key.decrypted_api_key,
        "secret": key.decrypted_api_secret,
        "environment": key.extra_data.get("environment", "sandbox"),
        "label": key.label,
    }


@router.post("/plaid/connect-api-key")
def plaid_connect_api_key(request, payload: PlaidApiKeySchema):
    """Store user-provided Plaid credentials and validate them."""
    from apps.users.services.plaid_client import PlaidClient
    from .models import ApiKeyIntegration, IntegrationLog

    user = request.auth
    client = PlaidClient.with_credentials(
        client_id=payload.client_id,
        secret=payload.secret,
        environment=payload.environment,
    )
    if not client.health_check():
        return {"success": False, "error": "Plaid credentials validation failed"}

    key, _ = ApiKeyIntegration.objects.update_or_create(
        user=user,
        service="plaid",
        defaults={
            "label": payload.label,
            "api_key": payload.client_id,
            "api_secret": payload.secret,
            "extra_data": {"environment": payload.environment},
            "is_active": True,
            "status": "active",
        },
    )
    IntegrationLog.objects.create(
        user=user,
        service="plaid",
        api_key=key,
        level="success",
        message="Plaid API credentials validated and saved",
    )
    return {"success": True, "id": str(key.id)}


@router.get("/plaid/clusters")
def plaid_clusters(request):
    """Return transaction clusters for the dashboard."""
    from collections import Counter

    from apps.document_chunks.models import DocumentChunk

    user = request.auth
    qs = DocumentChunk.objects.filter(
        stream__user=user, stream__source_type="plaid"
    ).values_list("cluster_category", flat=True)
    counts = Counter(qs)
    CLUSTER_IMAGES = {
        "receipt": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=240&fit=crop",
        "travel": "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=240&fit=crop",
        "shopping": "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=400&h=240&fit=crop",
        "subscription": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400&h=240&fit=crop",
        "finance": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400&h=240&fit=crop",
        "shipping": "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&h=240&fit=crop",
        "health": "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=400&h=240&fit=crop",
        "general": "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=400&h=240&fit=crop",
    }
    clusters = [
        {
            "category": cat,
            "count": count,
            "image_url": CLUSTER_IMAGES.get(cat, CLUSTER_IMAGES["general"]),
            "label": cat.replace("_", " ").title(),
        }
        for cat, count in counts.most_common()
    ]
    return {"clusters": clusters, "total": sum(counts.values()), "connected": bool(user.plaid_access_token)}


@router.post("/plaid/sync-clusters")
def plaid_sync_clusters(request, connection_id: str = ""):
    from .models import IntegrationConnection

    user = request.auth
    has_connection = IntegrationConnection.objects.filter(
        user=user, service="plaid", is_active=True
    ).exists()
    if not has_connection and not user.plaid_access_token:
        return {"success": False, "error": "Plaid not connected"}
    try:
        from .services.transaction_clustering import index_plaid_transactions

        if connection_id:
            conn = IntegrationConnection.objects.get(
                id=connection_id, user=user, service="plaid", is_active=True
            )
            result = index_plaid_transactions(user, connection=conn)
        else:
            result = index_plaid_transactions(user)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/plaid/accounts")
def plaid_accounts(request):
    from apps.users.services import PlaidClient
    from .models import IntegrationConnection

    user = request.auth
    connections = IntegrationConnection.objects.filter(
        user=user, service="plaid", is_active=True
    )
    if not connections.exists() and not user.plaid_access_token:
        return {"accounts": [], "count": 0, "error": "Plaid not connected"}

    all_accounts = []
    errors = []
    for conn in connections:
        try:
            plaid = PlaidClient(user, connection=conn)
            accounts = plaid.get_accounts()
            for acc in accounts:
                acc["connection_id"] = str(conn.id)
                acc["connection_label"] = conn.account_label
            all_accounts.extend(accounts)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Plaid accounts error for {conn.id}: {e}")
            errors.append(str(e))

    if not connections.exists() and user.plaid_access_token:
        # Legacy fallback
        try:
            plaid = PlaidClient(user)
            all_accounts.extend(plaid.get_accounts())
        except Exception as e:
            errors.append(str(e))

    return {
        "accounts": all_accounts,
        "count": len(all_accounts),
        "errors": errors if errors else None,
    }


@router.get("/plaid/transactions")
def plaid_transactions(request, days: int = Query(30), count: int = Query(100)):
    from datetime import datetime, timedelta

    from apps.users.services import PlaidClient
    from .models import IntegrationConnection

    user = request.auth
    connections = IntegrationConnection.objects.filter(
        user=user, service="plaid", is_active=True
    )
    if not connections.exists() and not user.plaid_access_token:
        return {"transactions": [], "count": 0, "error": "Plaid not connected"}

    end = datetime.now()
    start = end - timedelta(days=days)
    all_transactions = []
    errors = []
    for conn in connections:
        try:
            plaid = PlaidClient(user, connection=conn)
            transactions = plaid.get_transactions(start_date=start, end_date=end, count=count)
            for tx in transactions:
                tx["connection_id"] = str(conn.id)
                tx["connection_label"] = conn.account_label
            all_transactions.extend(transactions)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Plaid transactions error for {conn.id}: {e}")
            errors.append(str(e))

    if not connections.exists() and user.plaid_access_token:
        # Legacy fallback
        try:
            plaid = PlaidClient(user)
            all_transactions.extend(plaid.get_transactions(start_date=start, end_date=end, count=count))
        except Exception as e:
            errors.append(str(e))

    return {
        "transactions": all_transactions,
        "count": len(all_transactions),
        "errors": errors if errors else None,
    }


@router.get("/plaid/balances")
def plaid_balances(request):
    from apps.users.services import PlaidClient
    from .models import IntegrationConnection

    user = request.auth
    connections = IntegrationConnection.objects.filter(
        user=user, service="plaid", is_active=True
    )
    if not connections.exists() and not user.plaid_access_token:
        return {"balances": [], "error": "Plaid not connected"}

    all_balances = []
    errors = []
    for conn in connections:
        try:
            plaid = PlaidClient(user, connection=conn)
            balances = plaid.get_balances()
            for b in balances:
                b["connection_id"] = str(conn.id)
                b["connection_label"] = conn.account_label
            all_balances.extend(balances)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Plaid balances error for {conn.id}: {e}")
            errors.append(str(e))

    if not connections.exists() and user.plaid_access_token:
        try:
            plaid = PlaidClient(user)
            all_balances.extend(plaid.get_balances())
        except Exception as e:
            errors.append(str(e))

    return {"balances": all_balances, "errors": errors if errors else None}


# ─── Canva ──────────────────────────────────────────────────────────


def _get_canva_token(user):
    if user.canva_access_token:
        return user.canva_access_token
    from .models import ApiKeyIntegration

    key = ApiKeyIntegration.objects.filter(user=user, service="canva", is_active=True).first()
    if key:
        return key.decrypted_api_key
    return None


@router.get("/canva/status")
def canva_status(request):
    user = request.auth
    return {"connected": bool(_get_canva_token(user))}


@router.get("/canva/designs")
def canva_designs(request, query: str = "", limit: int = Query(20)):
    """List user's Canva designs."""
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    token = _get_canva_token(user)
    if not token:
        return {"designs": [], "count": 0, "error": "Canva not connected"}

    try:
        client = CanvaClient(token)
        designs = client.get_designs(query=query or None, limit=limit)
        return {"designs": designs, "count": len(designs)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva designs error: {e}")
        return {
            "designs": [],
            "count": 0,
            "error": f"Failed to fetch designs: {str(e)}",
        }


@router.get("/canva/design/{design_id}")
def canva_design_detail(request, design_id: str):
    """Get Canva design details."""
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    token = _get_canva_token(user)
    if not token:
        return {"error": "Canva not connected"}

    try:
        client = CanvaClient(token)
        design = client.get_design(design_id)
        return design
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva design detail error: {e}")
        return {"error": f"Failed to fetch design: {str(e)}"}


@router.get("/canva/brand-templates")
def canva_brand_templates(request):
    """Get brand templates."""
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    if not user.canva_access_token:
        return {"templates": [], "count": 0, "error": "Canva not connected"}

    try:
        client = CanvaClient(user.canva_access_token)
        templates = client.get_brand_templates()
        return {"templates": templates, "count": len(templates)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva brand templates error: {e}")
        return {
            "templates": [],
            "count": 0,
            "error": f"Failed to fetch templates: {str(e)}",
        }


@router.post("/canva/competitor-monitor")
def canva_competitor_monitor(request, payload: CanvaCompetitorSchema):
    """
    Monitor Canva design trends by tracking competitor keywords.
    Searches the public template library for trending designs.
    """
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    token = _get_canva_token(user)
    if not token:
        return {"error": "Canva not connected"}

    try:
        client = CanvaClient(token)
        result = client.track_competitor_keywords(
            keywords=payload.keywords,
            max_results=payload.max_results,
        )
        return result
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva competitor monitor error: {e}")
        return {"error": f"Failed to monitor competitors: {str(e)}"}


@router.post("/canva/search-templates")
def canva_search_templates(request, payload: CanvaSearchSchema):
    """Search Canva's public template library."""
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    token = _get_canva_token(user)
    if not token:
        return {"templates": [], "count": 0, "error": "Canva not connected"}

    try:
        client = CanvaClient(token)
        templates = client.search_public_designs(
            keywords=payload.keywords,
            category=payload.category,
        )
        return {"templates": templates, "count": len(templates)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva search templates error: {e}")
        return {
            "templates": [],
            "count": 0,
            "error": f"Failed to search templates: {str(e)}",
        }


# ─── Kijiji ──────────────────────────────────────────────────────────


@router.post("/kijiji/search")
def kijiji_search(request, payload: KijijiSearchSchema):
    from apps.users.services import KijijiScraperService

    try:
        scraper = KijijiScraperService(user=request.auth)
        listings = scraper.search_listings(
            query=payload.query,
            location=payload.location,
            category=payload.category,
            min_price=payload.min_price,
            max_price=payload.max_price,
        )
        return {"listings": listings, "count": len(listings)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Kijiji search error: {e}")
        return {"listings": [], "count": 0, "error": f"Kijiji search failed: {str(e)}"}


@router.get("/kijiji/messages")
def kijiji_messages(request, limit: int = Query(50)):
    from apps.users.services import KijijiScraperService

    try:
        scraper = KijijiScraperService(user=request.auth)
        messages = scraper.get_messages(limit=limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Kijiji messages error: {e}")
        return {
            "messages": [],
            "count": 0,
            "error": f"Kijiji messages failed: {str(e)}",
        }


# ─── Jira ─────────────────────────────────────────────────────────────


def _jira_oauth_connected(user):
    return bool(user.jira_oauth_access_token)


def _get_jira_client(user):
    """Return a JiraClient using OAuth if available, otherwise API token."""
    from apps.users.services.jira_client import JiraClient

    if _jira_oauth_connected(user):
        site_url = user.jira_site_url or "https://api.atlassian.com"
        return JiraClient(site_url=site_url, oauth_token=user.jira_oauth_access_token)
    if user.jira_site_url and user.jira_api_token and user.jira_email:
        return JiraClient(
            site_url=user.jira_site_url,
            email=user.jira_email,
            api_token=user.jira_api_token,
        )
    return None


@router.get("/jira/status")
def jira_status(request):
    """Check Jira connection status (OAuth or API token)."""
    user = request.auth
    oauth_connected = _jira_oauth_connected(user)
    token_connected = bool(user.jira_site_url and user.jira_api_token and user.jira_email)
    return {
        "connected": oauth_connected or token_connected,
        "oauth_connected": oauth_connected,
        "token_connected": token_connected,
        "site_url": user.jira_site_url or "",
    }


@router.post("/jira/configure")
def jira_configure(request, payload: JiraConfigureSchema):
    """Configure Jira connection."""
    from apps.users.services.jira_client import JiraClient

    user = request.auth
    client = JiraClient(
        site_url=payload.site_url,
        email=payload.email,
        api_token=payload.api_token,
    )
    result = client.test_connection()
    if result.get("success"):
        user.jira_site_url = payload.site_url
        user.jira_email = payload.email
        user.jira_api_token = payload.api_token
        user.save(update_fields=["jira_site_url", "jira_email", "jira_api_token"])
        return {"success": True, "account_id": result.get("account_id"), "display_name": result.get("display_name")}
    return {"success": False, "error": result.get("error", "Connection failed")}


@router.get("/jira/projects")
def jira_projects(request):
    """List Jira projects."""
    user = request.auth
    client = _get_jira_client(user)
    if not client:
        return {"projects": [], "count": 0, "error": "Jira not configured"}

    try:
        projects = client.get_projects()
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Jira projects error: {e}")
        return {"projects": [], "count": 0, "error": str(e)}


@router.post("/jira/issues")
def jira_issues(request, payload: JiraSyncSchema):
    """Fetch Jira issues by project or JQL."""
    user = request.auth
    client = _get_jira_client(user)
    if not client:
        return {"issues": [], "count": 0, "error": "Jira not configured"}

    try:
        issues = client.get_issues(
            project_key=payload.project_key,
            jql=payload.jql,
            max_results=payload.max_results,
        )
        return {"issues": issues, "count": len(issues)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Jira issues error: {e}")
        return {"issues": [], "count": 0, "error": str(e)}


@router.post("/jira/sync")
def jira_sync(request, payload: JiraSyncSchema):
    """Sync Jira issues into the RAG data store."""
    from apps.document_chunks.models import DocumentChunk
    from apps.data_streams.models import DataStream

    user = request.auth
    client = _get_jira_client(user)
    if not client:
        return {"success": False, "error": "Jira not configured"}

    try:
        issues = client.get_issues(
            project_key=payload.project_key,
            jql=payload.jql,
            max_results=payload.max_results,
        )

        stream, _ = DataStream.objects.get_or_create(
            user=user,
            source_type="jira",
            defaults={"payload": {"project_key": payload.project_key or "all"}},
        )

        chunks_created = 0
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

            chunk = DocumentChunk.objects.create(
                stream=stream,
                content=text,
                cluster_category="jira",
                embedding=[],
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
            from apps.document_chunks.services.embedding_generation import _generate_embedding_sync

            chunk.embedding = _generate_embedding_sync(text)
            chunk.save(update_fields=["embedding"])
            chunks_created += 1

        from apps.integrations.tasks import _update_connection as update_sync_log
        update_sync_log(user, "jira", success=True, items=chunks_created)

        return {"success": True, "issues_synced": chunks_created}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Jira sync error: {e}")
        try:
            from apps.integrations.tasks import _update_connection as update_sync_log
            update_sync_log(user, "jira", success=False, error=str(e))
        except Exception:
            pass
        return {"success": False, "error": str(e)}


@router.post("/jira/search")
def jira_search(request, payload: JiraSyncSchema):
    """Search Jira issues and return RAG-ready text snippets."""
    user = request.auth
    client = _get_jira_client(user)
    if not client:
        return {"results": [], "count": 0, "error": "Jira not configured"}

    try:
        if payload.project_key:
            results = client.issues_for_rag(project_key=payload.project_key, max_results=payload.max_results)
        elif payload.jql:
            issues = client.get_issues(jql=payload.jql, max_results=payload.max_results)
            results = [client._rag_result(issue) for issue in issues]
        else:
            return {"results": [], "count": 0, "error": "Provide project_key or jql"}
        return {"results": results, "count": len(results)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Jira search error: {e}")
        return {"results": [], "count": 0, "error": str(e)}


# ─── Email clusters ──────────────────────────────────────────────────


@router.get("/email/clusters")
def email_clusters(request):
    """Return email clusters for the dashboard."""
    from collections import Counter

    from apps.document_chunks.models import DocumentChunk

    user = request.auth
    qs = DocumentChunk.objects.filter(
        stream__user=user, stream__source_type__in=["email", "gmail"]
    ).values_list("cluster_category", flat=True)
    counts = Counter(qs)
    CLUSTER_IMAGES = {
        "job_alert": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=400&h=240&fit=crop",
        "job_offer": "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400&h=240&fit=crop",
        "job_interview": "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=400&h=240&fit=crop",
        "job_rejection": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&h=240&fit=crop",
        "finance": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&h=240&fit=crop",
        "receipt": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400&h=240&fit=crop",
        "newsletter": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400&h=240&fit=crop",
        "security": "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=400&h=240&fit=crop",
        "calendar": "https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=400&h=240&fit=crop",
        "meeting": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=400&h=240&fit=crop",
        "social": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=400&h=240&fit=crop",
        "shipping": "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&h=240&fit=crop",
        "travel": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=400&h=240&fit=crop",
        "marketing": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=240&fit=crop",
        "urgent": "https://images.unsplash.com/photo-1504384764586-bb4cdc1707b0?w=400&h=240&fit=crop",
        "recrutement": "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=400&h=240&fit=crop",
        "general": "https://images.unsplash.com/photo-1557200134-90327ee9fafa?w=400&h=240&fit=crop",
    }
    clusters = [
        {
            "category": cat,
            "count": count,
            "image_url": CLUSTER_IMAGES.get(cat, CLUSTER_IMAGES["general"]),
            "label": cat.replace("_", " ").title(),
        }
        for cat, count in counts.most_common()
    ]
    return {
        "clusters": clusters,
        "total": sum(counts.values()),
        "connected": bool(user.email_imap_host or user.google_access_token),
    }


@router.get("/email/clusters/{category}")
def email_cluster_details(request, category: str):
    """Return the email messages inside a single cluster category."""
    from apps.document_chunks.models import DocumentChunk

    user = request.auth
    chunks = (
        DocumentChunk.objects.filter(
            stream__user=user,
            stream__source_type__in=["email", "gmail"],
            cluster_category=category,
        )
        .order_by("-created_at")
        .values(
            "id",
            "content",
            "cluster_category",
            "metadata",
            "created_at",
        )[:200]
    )
    messages = []
    for c in chunks:
        meta = c["metadata"] or {}
        content = c["content"] or ""
        messages.append(
            {
                "id": str(c["id"]),
                "subject": meta.get("subject", ""),
                "sender": meta.get("sender", meta.get("from", "")),
                "date": meta.get("date", ""),
                "content": content,
                "category": c["cluster_category"],
                "mock": bool(meta.get("mock", False)),
            }
        )
    return {
        "category": category,
        "messages": messages,
        "count": len(messages),
    }


# ─── OAuth URLs ──────────────────────────────────────────────────────


@router.get("/oauth/google")
def google_oauth_url(request):
    from urllib.parse import quote

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    redirect_uri = getattr(
        settings,
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/google/callback",
    )
    state = str(getattr(request.auth, "id", ""))
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&redirect_uri={quote(redirect_uri, safe='')}&"
        f"response_type=code&scope={quote(' '.join(scopes))}&"
        f"access_type=offline&prompt=consent&state={state}"
    )
    return {"url": url}


@router.get("/oauth/google/callback", auth=None)
def google_oauth_callback(request, code: str = "", state: str = "", error: str = ""):
    """Exchange Google OAuth code for tokens and store on the user."""
    from django.contrib.auth import get_user_model
    from django.http import HttpResponseRedirect
    import httpx

    frontend = getattr(
        settings,
        "FRONTEND_OAUTH_REDIRECT_URL",
        getattr(settings, "FRONTEND_URL", "http://localhost:3000"),
    )
    if error or not code:
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=google")

    User = get_user_model()
    try:
        user = User.objects.get(id=state) if state else None
    except Exception:
        user = None
    if not user:
        return HttpResponseRedirect(f"{frontend}?oauth=nouser&service=google")

    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = getattr(
        settings,
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/google/callback",
    )
    try:
        with httpx.Client(timeout=30) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            data = token_resp.json()
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if access:
            user.google_access_token = access
            fields = ["google_access_token"]
            if refresh:
                user.google_refresh_token = refresh
                fields.append("google_refresh_token")
            user.jc_email_connected = True
            user.jc_email_provider = "gmail"
            fields.extend(["jc_email_connected", "jc_email_provider"])
            user.save(update_fields=fields)

            # Store as a multi-account connection as well.
            from .models import IntegrationConnection

            label = user.email or "Gmail"
            conn, _ = IntegrationConnection.objects.get_or_create(
                user=user,
                service="gmail",
                account_label=label,
                defaults={
                    "access_token": access,
                    "refresh_token": refresh or "",
                    "status": "active",
                    "is_active": True,
                },
            )
            conn.access_token = access
            if refresh:
                conn.refresh_token = refresh
            conn.is_active = True
            conn.save(update_fields=["access_token", "refresh_token", "is_active"])

            try:
                from .tasks import sync_gmail_for_user

                sync_gmail_for_user.delay(str(user.id))
            except Exception:
                pass
        return HttpResponseRedirect(f"{frontend}?oauth=success&service=google")
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Google OAuth callback failed: {e}")
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=google")


@router.get("/oauth/canva")
def canva_oauth_url(request):
    from urllib.parse import quote

    client_id = getattr(settings, "CANVA_CLIENT_ID", "")
    redirect_uri = getattr(
        settings,
        "CANVA_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/canva/callback",
    )
    state = str(getattr(request.auth, "id", ""))
    scopes = quote("design:meta:read design:meta:write design:content:read folder:meta:read")
    url = (
        f"https://www.canva.com/api/oauth/authorize?"
        f"response_type=code&client_id={client_id}"
        f"&redirect_uri={quote(redirect_uri, safe='')}&scope={scopes}&state={state}"
    )
    return {"url": url}


@router.get("/oauth/canva/callback", auth=None)
def canva_oauth_callback(request, code: str = "", state: str = "", error: str = ""):
    """Exchange Canva OAuth code for tokens and store on the user."""
    from django.contrib.auth import get_user_model
    from django.http import HttpResponseRedirect
    import httpx

    frontend = getattr(
        settings,
        "FRONTEND_OAUTH_REDIRECT_URL",
        getattr(settings, "FRONTEND_URL", "http://localhost:3000"),
    )
    if error or not code:
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=canva")

    User = get_user_model()
    try:
        user = User.objects.get(id=state) if state else None
    except Exception:
        user = None
    if not user:
        return HttpResponseRedirect(f"{frontend}?oauth=nouser&service=canva")

    client_id = getattr(settings, "CANVA_CLIENT_ID", "")
    client_secret = getattr(settings, "CANVA_CLIENT_SECRET", "")
    redirect_uri = getattr(
        settings,
        "CANVA_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/canva/callback",
    )
    try:
        with httpx.Client(timeout=30) as client:
            token_resp = client.post(
                "https://api.canva.com/rest/v1/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            data = token_resp.json()
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if access:
            user.canva_access_token = access
            fields = ["canva_access_token"]
            if refresh:
                user.canva_refresh_token = refresh
                fields.append("canva_refresh_token")
            user.save(update_fields=fields)

            from .models import IntegrationConnection, IntegrationLog

            conn, _ = IntegrationConnection.objects.get_or_create(
                user=user,
                service="canva",
                account_label=user.email or "Canva",
                defaults={
                    "access_token": access,
                    "refresh_token": refresh or "",
                    "status": "active",
                    "is_active": True,
                },
            )
            conn.access_token = access
            if refresh:
                conn.refresh_token = refresh
            conn.is_active = True
            conn.save(update_fields=["access_token", "refresh_token", "is_active"])
            IntegrationLog.objects.create(
                user=user,
                service="canva",
                connection=conn,
                level="success",
                message="Canva connected via OAuth2",
            )
            try:
                from .tasks import sync_canva_for_user

                sync_canva_for_user.delay(str(user.id))
            except Exception:
                pass
        return HttpResponseRedirect(f"{frontend}?oauth=success&service=canva")
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Canva OAuth callback failed: {e}")
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=canva")


@router.get("/oauth/jira")
def jira_oauth_url(request):
    """Start Atlassian OAuth 2.0 (3LO) flow."""
    from urllib.parse import quote

    client_id = getattr(settings, "JIRA_OAUTH_CLIENT_ID", "")
    redirect_uri = getattr(
        settings,
        "JIRA_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/jira/callback",
    )
    state = str(getattr(request.auth, "id", ""))
    scopes = quote("read:jira-user read:jira-work offline_access")
    url = (
        f"https://auth.atlassian.com/authorize?"
        f"audience=api.atlassian.com&client_id={client_id}"
        f"&scope={scopes}&redirect_uri={quote(redirect_uri, safe='')}"
        f"&state={state}&response_type=code&prompt=consent"
    )
    return {"url": url}


@router.get("/oauth/jira/callback", auth=None)
def jira_oauth_callback(request, code: str = "", state: str = "", error: str = ""):
    """Exchange Atlassian OAuth code for tokens and store on the user."""
    from django.contrib.auth import get_user_model
    from django.http import HttpResponseRedirect
    import httpx

    frontend = getattr(
        settings,
        "FRONTEND_OAUTH_REDIRECT_URL",
        getattr(settings, "FRONTEND_URL", "http://localhost:3000"),
    )
    if error or not code:
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=jira")

    User = get_user_model()
    try:
        user = User.objects.get(id=state) if state else None
    except Exception:
        user = None
    if not user:
        return HttpResponseRedirect(f"{frontend}?oauth=nouser&service=jira")

    client_id = getattr(settings, "JIRA_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "JIRA_OAUTH_CLIENT_SECRET", "")
    redirect_uri = getattr(
        settings,
        "JIRA_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/integrations/oauth/jira/callback",
    )
    try:
        with httpx.Client(timeout=30) as client:
            token_resp = client.post(
                "https://auth.atlassian.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            data = token_resp.json()
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if access:
            user.jira_oauth_access_token = access
            fields = ["jira_oauth_access_token"]
            if refresh:
                user.jira_oauth_refresh_token = refresh
                fields.append("jira_oauth_refresh_token")

            # Try to discover the Jira site URL from accessible resources.
            try:
                with httpx.Client(timeout=30) as resources_client:
                    resources_resp = resources_client.get(
                        "https://api.atlassian.com/oauth/token/accessible-resources",
                        headers={"Authorization": f"Bearer {access}"},
                    )
                    resources_resp.raise_for_status()
                    resources = resources_resp.json()
                    if resources:
                        site_url = resources[0].get("url", "")
                        if site_url:
                            user.jira_site_url = site_url
                            fields.append("jira_site_url")
            except Exception as resource_err:
                import logging
                logging.getLogger(__name__).warning(f"Could not fetch Jira accessible resources: {resource_err}")

            user.save(update_fields=fields)

            from .models import IntegrationConnection, IntegrationLog

            conn, _ = IntegrationConnection.objects.get_or_create(
                user=user,
                service="jira",
                account_label=user.email or "Jira",
                defaults={
                    "access_token": access,
                    "refresh_token": refresh or "",
                    "status": "active",
                    "is_active": True,
                },
            )
            conn.access_token = access
            if refresh:
                conn.refresh_token = refresh
            conn.is_active = True
            conn.save(update_fields=["access_token", "refresh_token", "is_active"])
            IntegrationLog.objects.create(
                user=user,
                service="jira",
                connection=conn,
                level="success",
                message="Jira connected via OAuth2",
            )
        return HttpResponseRedirect(f"{frontend}?oauth=success&service=jira")
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Jira OAuth callback failed: {e}")
        return HttpResponseRedirect(f"{frontend}?oauth=error&service=jira")


# ─── LLM Configuration ─────────────────────────────────────────────────
# Import LLM router and add it to the main router
from .llm_api import router as llm_router

router.add_router("/llm-configurations", llm_router)


# ─── API Key Integrations ─────────────────────────────────────────────


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _api_key_to_dict(key: "ApiKeyIntegration") -> dict:
    return {
        "id": str(key.id),
        "service": key.service,
        "label": key.label,
        "api_key_masked": _mask_key(key.decrypted_api_key),
        "api_secret_masked": _mask_key(key.decrypted_api_secret),
        "extra_data": key.extra_data,
        "is_active": key.is_active,
        "status": key.status,
        "last_tested": key.last_tested.isoformat() if key.last_tested else None,
        "last_error": key.last_error,
        "created_at": key.created_at.isoformat(),
        "updated_at": key.updated_at.isoformat(),
    }


@router.get("/api-keys", response=list[ApiKeyResponseSchema])
def list_api_keys(request):
    from .models import ApiKeyIntegration

    user = request.auth
    keys = ApiKeyIntegration.objects.filter(user=user)
    return [_api_key_to_dict(k) for k in keys]


@router.post("/api-keys", response=ApiKeyResponseSchema)
def create_api_key(request, payload: ApiKeyCreateSchema):
    from .models import ApiKeyIntegration, IntegrationLog

    user = request.auth
    key = ApiKeyIntegration.objects.create(
        user=user,
        service=payload.service,
        label=payload.label,
        api_key=payload.api_key,
        api_secret=payload.api_secret or "",
        extra_data=payload.extra_data or {},
        status="unknown",
    )
    IntegrationLog.objects.create(
        user=user,
        service=key.service,
        api_key=key,
        level="info",
        message=f"API key '{key.label}' created",
    )
    return _api_key_to_dict(key)


@router.patch("/api-keys/{key_id}", response=ApiKeyResponseSchema)
def update_api_key(request, key_id: str, payload: ApiKeyUpdateSchema):
    from .models import ApiKeyIntegration, IntegrationLog

    user = request.auth
    key = ApiKeyIntegration.objects.get(id=key_id, user=user)
    if payload.label is not None:
        key.label = payload.label
    if payload.api_key is not None:
        key.api_key = payload.api_key
    if payload.api_secret is not None:
        key.api_secret = payload.api_secret
    if payload.extra_data is not None:
        key.extra_data = payload.extra_data
    if payload.is_active is not None:
        key.is_active = payload.is_active
        key.status = "disabled" if not key.is_active else "unknown"
    key.save()
    IntegrationLog.objects.create(
        user=user,
        service=key.service,
        api_key=key,
        level="info",
        message=f"API key '{key.label}' updated",
    )
    return _api_key_to_dict(key)


@router.delete("/api-keys/{key_id}")
def delete_api_key(request, key_id: str):
    from .models import ApiKeyIntegration, IntegrationLog

    user = request.auth
    key = ApiKeyIntegration.objects.get(id=key_id, user=user)
    IntegrationLog.objects.create(
        user=user,
        service=key.service,
        level="warning",
        message=f"API key '{key.label}' deleted",
    )
    key.delete()
    return {"success": True, "id": key_id}


@router.post("/api-keys/{key_id}/test", response=ApiKeyTestResponseSchema)
def test_api_key(request, key_id: str):
    from django.utils import timezone

    from .models import ApiKeyIntegration, IntegrationLog
    from .tasks import test_api_key_integration

    user = request.auth
    key = ApiKeyIntegration.objects.get(id=key_id, user=user)
    try:
        result = test_api_key_integration(user, key)
    except Exception as exc:
        result = {"success": False, "status": "error", "error": str(exc)}

    key.status = "active" if result.get("success") else "error"
    key.last_tested = timezone.now()
    key.last_error = result.get("error") or ""
    key.save(update_fields=["status", "last_tested", "last_error"])

    IntegrationLog.objects.create(
        user=user,
        service=key.service,
        api_key=key,
        level="success" if result.get("success") else "error",
        message="API key test " + ("succeeded" if result.get("success") else "failed"),
        metadata={"error": result.get("error")},
    )
    return result


# ─── Integration State Logs ───────────────────────────────────────────


@router.get("/logs", response=list[IntegrationLogResponseSchema])
def list_integration_logs(request, service: str = "", limit: int = 50):
    from .models import IntegrationLog

    user = request.auth
    qs = IntegrationLog.objects.filter(user=user)
    if service:
        qs = qs.filter(service=service)
    return [
        {
            "id": str(log.id),
            "service": log.service,
            "level": log.level,
            "message": log.message,
            "metadata": log.metadata,
            "created_at": log.created_at.isoformat(),
        }
        for log in qs[:limit]
    ]
