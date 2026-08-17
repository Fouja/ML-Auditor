"""
Email clustering: classify email messages into RAG categories and persist them
as pgvector-backed DocumentChunks.

Classify strategy (cheap first, smarter on tie-break):
  1. Heuristic keyword classifier over subject + sender + body snippet. Fast,
     deterministic, zero API cost, and accurate for the noisy daily email mix.
  2. Only when the heuristic lands on "general" do we ask the NIM chat model to
     refine the category. The LLM call is wrapped defensively so a slow/absent
     endpoint degrades to the heuristic label instead of failing the sync.

Every message is persisted as a single chunk deduplicated by its email
``Message-ID`` (stored in ``metadata.message_id``), so re-syncing the same
folder is idempotent.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

CATEGORIES = [
    "recrutement",
    "urgent",
    "finance",
    "kijiji_deal",
    "calendar",
    "general",
    "jira",
    "social",
    "job_alert",
    "job_event",
    "networking",
    "receipt",
    "security",
    "newsletter",
    "project_idea",
    "job_offer",
    "job_rejection",
    "job_interview",
    "subscription",
    "shipping",
    "marketing",
    "survey",
    "travel",
    "meeting",
    "legal",
    "document",
]

# Ordered most-specific first; the first match wins.
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "security",
        (
            "security alert", "unusual activity", "password reset", "account locked",
            "sign-in", "sign in", "2-step", "two-factor", "two factor", "verification",
            "verify your", "one-time", "one time", "otp", "authentication",
            "unusual sign", "recovery code", "suspicious",
        ),
    ),
    (
        "receipt",
        (
            "receipt", "invoice", "payment confirmed", "order confirmation",
            "your order", "order #", "transaction", "purchase", "statement",
            "billing", "payment received",
        ),
    ),
    (
        "job_offer",
        (
            "job offer", "offer letter", "offer of employment", "we would like to offer",
            "you're hired", "you are hired", "welcome to the team", "employment contract",
            "your start date", "signing bonus", "offer for the position", "to offer you the",
        ),
    ),
    (
        "job_interview",
        (
            "interview invitation", "interview scheduled", "phone screen",
            "technical interview", "panel interview", "interview confirmation",
            "interview", "invite you to interview", "availability for an interview",
            "schedule an interview",
        ),
    ),
    (
        "job_rejection",
        (
            "not moving forward", "regret to inform", "will not be proceeding",
            "other candidates", "position has been filled", "decided to move",
            "unsuccessful", "we will not be", "did not select", "won't be able to move",
            "not selected", "sorry to inform",
        ),
    ),
    (
        "job_event",
        (
            "career fair", "job fair", "hiring event", "open house", "career event",
            "recruitment event", "webinar", "workshop", "networking event",
            "meet and greet", "job expo",
        ),
    ),
    (
        "job_alert",
        (
            "job alert", "new job", "job recommendation", "matches for you",
            "jobs for you", "job digest", "job posting", "job opportunities",
            "opportunity for you", "new roles", "relevant roles", "vacancy",
            "position available", "we're hiring", "we are hiring", "career opportunities",
            "job match", "recommended jobs", "new openings",
        ),
    ),
    (
        "shipping",
        (
            "shipped", "shipping", "out for delivery", "tracking number", "package",
            "dispatch", "delivered", "shipment", "your delivery", "arrives",
            "carrier", "delivery status",
        ),
    ),
    (
        "subscription",
        (
            "subscription", "auto-renew", "auto renew", "your subscription",
            "membership", "plan renewal", "trial period", "free trial",
            "billing cycle", "renewal", "subscribed to", "plan will renew",
        ),
    ),
    (
        "travel",
        (
            "flight", "booking confirmation", "hotel", "boarding pass", "itinerary",
            "trip", "reservation", "car rental", "travel", "check-in", "check in",
            "departure", "ticket confirmation",
        ),
    ),
    (
        "networking",
        (
            "invitation to connect", "invitation to join", "connect with",
            "let's connect", "lets connect", "coffee chat", "introduction",
            "introduce you", "referral", "you have a connection", "mutual connection",
            "congratulations on", "reach out",
        ),
    ),
    (
        "survey",
        (
            "survey", "feedback", "we'd love your input", "quick question",
            "questionnaire", "tell us what you think", "rate your experience",
            "share your opinion", "minute survey", "help us improve",
        ),
    ),
    (
        "marketing",
        (
            "promo", "promotion", "special offer", "discount", "sale", "coupon",
            "exclusive offer", "limited time", "flash sale", "deals", "save up to",
            "biggest sale", "don't miss out", "dont miss out",
        ),
    ),
    (
        "meeting",
        (
            "conference call", "teams meeting", "google meet", "zoom", "stand-up",
            "stand up", "meeting minutes", "1:1", "catch up", "catch-up",
            "agenda for", "invited you to a meeting",
        ),
    ),
    (
        "legal",
        (
            "terms of service", "privacy policy", "agreement", "contract", "compliance",
            "nda", "non-disclosure", "attorney", "legal", "arbitration",
            "notice of", "licence agreement", "license agreement",
        ),
    ),
    (
        "document",
        (
            "please find attached", "attached document", "signed document",
            "fill out", "please sign", "document", "notarize", "scanned copy",
            "form attached",
        ),
    ),
    (
        "social",
        (
            "facebook", "instagram", "twitter", "youtube", "tiktok", "linkedin",
            "someone commented", "commented on", "reacted to", "new follower",
            "mentioned you", "notification", "like your", "shared your",
            "activity report", "friend request",
        ),
    ),
    (
        "newsletter",
        (
            "newsletter", "weekly digest", "monthly update", "what's new",
            "whats new", "top stories", "new blog", "blog post", "product update",
            "new from", "this week", "subscribed", "unsubscribe", "read more",
            "product roundup",
        ),
    ),
    (
        "project_idea",
        (
            "project idea", "idea for", "brainstorm", "prototype", "project proposal",
            "proof of concept", "side project", "experiment", "let's build",
            "build something", "concept",
        ),
    ),
    (
        "urgent",
        (
            "urgent", "asap", "immediately", "action required", "final notice",
            "time sensitive", "time-sensitive", "expires today", "due today",
            "deadline", "closes soon",
        ),
    ),
    (
        "calendar",
        (
            "calendar", "event invite", "meeting invite", "appointment",
            "reminder:", "reminder ", "rsvp", "schedule", "your meeting", "has invited",
            "invited you", "event reminder",
        ),
    ),
    (
        "finance",
        (
            "salary", "payroll", "pay stub", "bank", "transfer", "loan", "credit",
            "tax refund", "investment", "401k", "your payment", "direct deposit",
            "benefits", "insurance",
        ),
    ),
    (
        "kijiji_deal",
        (
            "kijiji", "marketplace", "for sale", "buyer", "seller",
            "interested in your ad", "your ad", "deal on",
        ),
    ),
    (
        "recrutement",
        (
            "recrutement", "candidature", "poste", "offre d'emploi", "entretien",
            "vous avez ete retenu", "cv", "processus de recrutement",
        ),
    ),
    (
        "jira",
        (
            "jira", "issue", "ticket", "sprint", "bug report", "assigned to you",
            "mentioned you in", "backlog",
        ),
    ),
]

# Subcategory rules are evaluated within an already-matched category, so they
# only add precision, never change the top-level label.
_SUBCATEGORY_RULES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "security": [
        ("two_factor", ("2-step", "two-factor", "two factor", "otp", "verification", "one-time", "one time", "authenticator")),
        ("password_reset", ("password reset", "recovery code", "reset your password")),
        ("login_alert", ("sign-in", "sign in", "unusual activity", "unusual sign", "new device", "suspicious")),
        ("account_locked", ("account locked", "locked out", "temporarily disabled")),
    ],
    "receipt": [
        ("order", ("order confirmation", "your order", "order #", "purchase")),
        ("payment", ("payment confirmed", "payment received", "transaction", "billing", "statement")),
        ("invoice", ("invoice", "your invoice")),
    ],
    "finance": [
        ("salary", ("salary", "payroll", "pay stub", "direct deposit", "bonus")),
        ("banking", ("bank", "transfer", "transaction", "overdraft")),
        ("credit", ("credit", "loan", "mortgage", "401k", "investment")),
        ("insurance", ("insurance", "benefits", "coverage")),
    ],
    "job_alert": [
        ("digest", ("job digest", "digest", "matches for you", "jobs for you", "recommended jobs")),
        ("new_role", ("new job", "job posting", "job opportunities", "vacancy", "new openings", "we're hiring", "we are hiring")),
    ],
    "travel": [
        ("flight", ("flight", "boarding pass", "departure", "itinerary")),
        ("hotel", ("hotel", "reservation", "check-in", "check in")),
        ("booking", ("booking confirmation", "car rental", "ticket confirmation")),
    ],
    "marketing": [
        ("promo", ("promo", "promotion", "special offer", "coupon", "exclusive offer")),
        ("sale", ("sale", "discount", "flash sale", "deals", "save up to")),
    ],
    "subscription": [
        ("renewal", ("renewal", "auto-renew", "auto renew", "plan will renew", "billing cycle")),
        ("trial", ("trial period", "free trial")),
        ("membership", ("membership", "subscribed to", "your subscription")),
    ],
    "job_interview": [
        ("phone_screen", ("phone screen", "preliminary", "screening call")),
        ("technical", ("technical interview", "coding", "technical")),
        ("scheduling", ("interview scheduled", "interview confirmation", "availability for an interview", "schedule an interview", "interview invitation")),
    ],
    "meeting": [
        ("video_call", ("zoom", "teams meeting", "google meet", "conference call")),
        ("sync", ("stand-up", "stand up", "1:1", "catch up", "catch-up", "sync")),
        ("minutes", ("meeting minutes", "agenda for")),
    ],
    "document": [
        ("signature", ("please sign", "signed document", "signature", "notarize")),
        ("attachment", ("please find attached", "attached document", "attachment", "form attached", "scanned copy")),
    ],
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).lower().strip()


def _keyword_hits(haystack: str) -> tuple[str, int]:
    """Return (first matching category, number of keyword hits)."""
    best: str | None = None
    best_hits = 0
    for category, keywords in _CATEGORY_KEYWORDS:
        hits = sum(1 for keyword in keywords if keyword in haystack)
        if hits > 0 and (best is None or hits > best_hits):
            best = category
            best_hits = hits
    return (best or "general", best_hits)


def heuristic_classify(subject: str, sender: str = "", body: str = "") -> str:
    """Classify an email from subject/sender/body using keyword signals."""
    haystack = _normalize(" ".join([subject or "", sender or "", (body or "")[:2000]]))
    category, _hits = _keyword_hits(haystack)
    return category


def _subcategory_for(category: str, haystack: str) -> str | None:
    rules = _SUBCATEGORY_RULES.get(category)
    if not rules:
        return None
    for subcategory, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return subcategory
    return None


def _llm_classify(subject: str, sender: str, body: str) -> str:
    """Ask NIM for a category; returns '' (→ caller falls back) on any failure."""
    try:
        import httpx
        from django.conf import settings

        api_key = getattr(settings, "NIM_API_KEY", "")
        if not api_key:
            try:
                from apps.integrations.models import LLMConfiguration

                cfg = LLMConfiguration.objects.filter(
                    provider="nvidia", is_active=True
                ).first()
                if cfg:
                    api_key = cfg.decrypted_api_key
            except Exception:
                pass
        if not api_key:
            return ""

        base_url = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")

        categories = ", ".join(CATEGORIES)
        prompt = (
            "Classify this email into exactly one category from this list: "
            f"{categories}.\n"
            f"Subject: {subject}\n"
            f"From: {sender}\n"
            f"Body: {(body or '')[:1500]}\n"
            'Reply with only the category key, e.g. "job_alert".'
        )
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8,
                },
            )
            resp.raise_for_status()
            answer = (resp.json()["choices"][0]["message"]["content"] or "").strip().lower()
        for candidate in CATEGORIES:
            if candidate in answer:
                return candidate
        return ""
    except Exception as exc:
        logger.warning(f"LLM email classify failed, falling back to heuristic: {exc}")
        return ""


def classify_email_detailed(subject: str, sender: str = "", body: str = "") -> dict:
    """Best-effort classification with subcategory and confidence.

    Returns ``{"category", "subcategory", "confidence"}``. Heuristic labels get
    a confidence scaled by how many distinct keywords matched; a "general"
    fallback is refined by NIM and, when that fails, carries a low confidence so
    downstream tooling knows the label is a guess.
    """
    haystack = _normalize(" ".join([subject or "", sender or "", (body or "")[:2000]]))
    category, hits = _keyword_hits(haystack)

    if category == "general":
        refined = _llm_classify(subject, sender, body)
        if refined and refined in CATEGORIES:
            category = refined
            confidence = round(min(0.9, 0.6 + 0.1 * hits), 2)
        else:
            confidence = 0.3
    else:
        confidence = round(min(0.98, 0.55 + 0.12 * hits), 2)

    return {
        "category": category,
        "subcategory": _subcategory_for(category, haystack),
        "confidence": confidence,
    }


def classify_email(subject: str, sender: str = "", body: str = "") -> str:
    """Return just the category key (backwards-compatible helper)."""
    return classify_email_detailed(subject, sender, body)["category"]


def _email_content(subject: str, sender: str, date: str, body: str, message_id: str) -> str:
    text = (body or "").strip()
    return (
        f"Email: {subject}\n"
        f"From: {sender}\n"
        f"Date: {date}\n"
        f"Message-ID: {message_id}\n"
        f"\n{text[:6000]}"
    ).strip()


def persist_email_chunk(stream, email: dict) -> dict:
    """Persist one email as a DocumentChunk, deduped by message_id.

    Returns {"created": bool, "message_id": str} so callers can count real new
    chunks vs. already-seen messages.
    """
    from apps.document_chunks.models import DocumentChunk
    from apps.document_chunks.services.embedding_generation import _generate_embedding_sync

    message_id = str(email.get("message_id") or email.get("id") or "").strip()
    if not message_id:
        match = _EMAIL_RE.search(str(email.get("from") or email.get("sender") or ""))
        message_id = match.group(0) if match else ""
    if not message_id:
        message_id = f"no-id-{abs(hash(str(email.get('subject'))))}"

    if DocumentChunk.objects.filter(stream=stream, metadata__message_id=message_id).exists():
        return {"created": False, "message_id": message_id}

    subject = str(email.get("subject") or "").strip()
    sender = str(email.get("from") or email.get("sender") or "").strip()
    body = str(email.get("body_text") or email.get("body") or email.get("snippet") or "").strip()
    date = str(email.get("date") or email.get("date_str") or "").strip()
    label = classify_email_detailed(subject, sender, body)
    category = label["category"]
    content = _email_content(subject, sender, date, body, message_id)

    DocumentChunk.objects.create(
        stream=stream,
        content=content,
        cluster_category=category,
        embedding=_generate_embedding_sync(content),
        metadata={
            "message_id": message_id,
            "subject": subject,
            "sender": sender,
            "date": date,
            "category": category,
            "subcategory": label["subcategory"],
            "confidence": label["confidence"],
        },
    )
    return {"created": True, "message_id": message_id}


def index_email_messages(user, messages: list[dict], source_type: str) -> dict:
    """Persist a batch of email messages into the user's RAG store.

    Returns a summary dict with counts of created/skipped chunks.
    """
    from apps.data_streams.models import DataStream

    stream, _ = DataStream.objects.get_or_create(
        user=user,
        source_type=source_type,
        defaults={"payload": {"source": source_type}},
    )
    created = 0
    skipped = 0
    for email in messages:
        result = persist_email_chunk(stream, email)
        if result.get("created"):
            created += 1
        else:
            skipped += 1
    return {"stream": str(stream.id), "created": created, "skipped": skipped, "total": len(messages)}
