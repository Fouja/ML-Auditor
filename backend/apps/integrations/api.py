"""
Integration API endpoints for external services.
Email (IMAP/SMTP + Gmail), Calendar, Plaid, Canva, Kijiji.
"""

from django.conf import settings
from ninja import Query, Router

from .schemas import (
    CalendarEventCreateSchema,
    CanvaCompetitorSchema,
    CanvaSearchSchema,
    EmailSendSchema,
    IMAPConfigSchema,
    IMAPSendSchema,
    KijijiSearchSchema,
    PlaidExchangeSchema,
)

router = Router()


# ─── Connection status ───────────────────────────────────────────────


@router.get("/status")
def integration_status(request):
    """Get status of all integrations."""
    user = request.auth
    return {
        "email": {
            "imap_connected": bool(user.email_imap_host),
            "gmail_connected": bool(user.google_access_token),
            "provider": user.email_provider or "custom",
        },
        "calendar": {"connected": bool(user.google_access_token)},
        "plaid": {"connected": bool(user.plaid_access_token)},
        "canva": {"connected": bool(user.canva_access_token)},
        "kijiji": {"connected": True},
    }


# ─── Generic IMAP/SMTP Email ────────────────────────────────────────


@router.post("/email/configure")
def email_configure(request, payload: IMAPConfigSchema):
    """Configure IMAP/SMTP settings for any email provider."""
    user = request.auth
    user.email_provider = payload.provider
    user.email_imap_host = payload.imap_host
    user.email_imap_port = payload.imap_port
    user.email_smtp_host = payload.smtp_host
    user.email_smtp_port = payload.smtp_port
    user.email_imap_password = payload.password
    user.email_use_ssl = payload.use_ssl
    user.save(
        update_fields=[
            "email_provider",
            "email_imap_host",
            "email_imap_port",
            "email_smtp_host",
            "email_smtp_port",
            "email_imap_password",
            "email_use_ssl",
        ]
    )
    return {"success": True}


@router.get("/email/status")
def email_status(request):
    """Check email IMAP/SMTP connection status."""
    user = request.auth
    connected = bool(user.email_imap_host and user.email_imap_password)
    return {
        "connected": connected,
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
    user = request.auth
    return {
        "connected": bool(user.google_access_token),
        "has_refresh_token": bool(user.google_refresh_token),
    }


@router.get("/gmail/sync")
def gmail_sync(request, max_results: int = Query(50)):
    from apps.users.services import GmailClient

    user = request.auth
    if not user.google_access_token:
        return {"messages": [], "count": 0, "error": "Gmail not connected"}

    try:
        gmail = GmailClient(user)
        messages = gmail.get_messages(max_results=max_results)
        results = []
        for msg in messages[:max_results]:
            full = gmail.get_message(msg["id"])
            headers = full.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")
            results.append(
                {
                    "id": msg["id"],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "snippet": full.get("snippet", ""),
                }
            )
        return {"messages": results, "count": len(results)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Gmail sync error: {e}")
        return {"messages": [], "count": 0, "error": f"Gmail sync failed: {str(e)}"}


@router.post("/gmail/send")
def gmail_send(request, payload: EmailSendSchema):
    from apps.users.services import GmailClient

    user = request.auth
    if not user.google_access_token:
        return {"success": False, "error": "Gmail not connected"}

    try:
        gmail = GmailClient(user)
        result = gmail.send_message(
            to=payload.to, subject=payload.subject, body=payload.body, cc=payload.cc
        )
        return {"success": True, "message_id": result.get("id")}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Gmail send error: {e}")
        return {"success": False, "error": f"Failed to send email: {str(e)}"}


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
    user = request.auth
    return {"connected": bool(user.plaid_access_token)}


@router.get("/plaid/link-token")
def plaid_link_token(request):
    from apps.users.services import PlaidClient

    user = request.auth
    try:
        plaid = PlaidClient(user)
        result = plaid.create_link_token(user_id=str(user.id))
        return {
            "link_token": result.get("link_token"),
            "expiration": result.get("expiration"),
        }
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid link token error: {e}")
        return {"link_token": None, "error": f"Failed to create link token: {str(e)}"}


@router.post("/plaid/exchange")
def plaid_exchange(request, payload: PlaidExchangeSchema):
    from apps.users.services import PlaidClient

    user = request.auth
    try:
        plaid = PlaidClient(user)
        result = plaid.exchange_public_token(payload.public_token)
        access_token = result.get("access_token")
        if access_token:
            user.plaid_access_token = access_token
            user.save(update_fields=["plaid_access_token"])
        return {"success": True}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid exchange error: {e}")
        return {"success": False, "error": f"Token exchange failed: {str(e)}"}


@router.get("/plaid/accounts")
def plaid_accounts(request):
    from apps.users.services import PlaidClient

    user = request.auth
    if not user.plaid_access_token:
        return {"accounts": [], "count": 0, "error": "Plaid not connected"}

    try:
        plaid = PlaidClient(user)
        accounts = plaid.get_accounts()
        return {"accounts": accounts, "count": len(accounts)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid accounts error: {e}")
        return {
            "accounts": [],
            "count": 0,
            "error": f"Failed to fetch accounts: {str(e)}",
        }


@router.get("/plaid/transactions")
def plaid_transactions(request, days: int = Query(30), count: int = Query(100)):
    from datetime import datetime, timedelta

    from apps.users.services import PlaidClient

    user = request.auth
    if not user.plaid_access_token:
        return {"transactions": [], "count": 0, "error": "Plaid not connected"}

    try:
        plaid = PlaidClient(user)
        end = datetime.now()
        start = end - timedelta(days=days)
        transactions = plaid.get_transactions(
            start_date=start, end_date=end, count=count
        )
        return {"transactions": transactions, "count": len(transactions)}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid transactions error: {e}")
        return {
            "transactions": [],
            "count": 0,
            "error": f"Failed to fetch transactions: {str(e)}",
        }


@router.get("/plaid/balances")
def plaid_balances(request):
    from apps.users.services import PlaidClient

    user = request.auth
    if not user.plaid_access_token:
        return {"balances": [], "error": "Plaid not connected"}

    try:
        plaid = PlaidClient(user)
        balances = plaid.get_balances()
        return {"balances": balances}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Plaid balances error: {e}")
        return {"balances": [], "error": f"Failed to fetch balances: {str(e)}"}


# ─── Canva ──────────────────────────────────────────────────────────


@router.get("/canva/status")
def canva_status(request):
    user = request.auth
    return {"connected": bool(user.canva_access_token)}


@router.get("/canva/designs")
def canva_designs(request, query: str = "", limit: int = Query(20)):
    """List user's Canva designs."""
    from apps.users.services.canva_client import CanvaClient

    user = request.auth
    if not user.canva_access_token:
        return {"designs": [], "count": 0, "error": "Canva not connected"}

    try:
        client = CanvaClient(user.canva_access_token)
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
    if not user.canva_access_token:
        return {"error": "Canva not connected"}

    try:
        client = CanvaClient(user.canva_access_token)
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
    if not user.canva_access_token:
        return {"error": "Canva not connected"}

    try:
        client = CanvaClient(user.canva_access_token)
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
    if not user.canva_access_token:
        return {"templates": [], "count": 0, "error": "Canva not connected"}

    try:
        client = CanvaClient(user.canva_access_token)
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


# ─── OAuth URLs ──────────────────────────────────────────────────────


@router.get("/oauth/google")
def google_oauth_url(request):
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    redirect_uri = "http://localhost:8000/api/integrations/oauth/google/callback"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&redirect_uri={redirect_uri}&"
        f"response_type=code&scope={' '.join(scopes)}&"
        f"access_type=offline&prompt=consent"
    )
    return {"url": url}


@router.get("/oauth/canva")
def canva_oauth_url(request):
    client_id = getattr(settings, "CANVA_CLIENT_ID", "")
    redirect_uri = "http://localhost:8000/api/integrations/oauth/canva/callback"
    url = (
        f"https://www.canva.com/api/oauth/authorize?"
        f"response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope=design:meta:read "
        f"design:meta:write design:content:read folder:meta:read"
    )
    return {"url": url}


# ─── LLM Configuration ─────────────────────────────────────────────────
# Import LLM router and add it to the main router
from .llm_api import router as llm_router

router.add_router("/llm-configurations", llm_router)
