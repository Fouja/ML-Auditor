"""
Cluster Plaid transactions into DocumentChunks for dashboard display / RAG.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Map free-text / Plaid categories onto DocumentChunk.CLUSTER_CATEGORIES keys.
_CATEGORY_MAP = {
    "food and drink": "receipt",
    "food": "receipt",
    "restaurants": "receipt",
    "groceries": "receipt",
    "travel": "travel",
    "transportation": "travel",
    "taxi": "travel",
    "gas": "travel",
    "shops": "marketing",
    "shopping": "marketing",
    "recreation": "subscription",
    "entertainment": "subscription",
    "payment": "finance",
    "transfer": "finance",
    "payroll": "finance",
    "deposit": "finance",
    "bank fees": "finance",
    "interest": "finance",
    "rent": "finance",
    "utilities": "finance",
    "service": "subscription",
    "subscription": "subscription",
    "healthcare": "document",
    "medical": "document",
    "general": "general",
}


def classify_transaction(name: str = "", category: Any = None, amount: float = 0) -> str:
    parts: List[str] = []
    if isinstance(category, list):
        parts.extend(str(c) for c in category)
    elif isinstance(category, str):
        parts.append(category)
    haystack = " ".join(parts + [name or ""]).lower()
    for key, mapped in _CATEGORY_MAP.items():
        if key in haystack:
            return mapped
    if amount and amount < 0:
        return "finance"
    return "general"


def index_plaid_transactions(user, days: int = 30, count: int = 100) -> Dict[str, Any]:
    from apps.data_streams.models import DataStream
    from apps.document_chunks.models import DocumentChunk
    from apps.users.services import PlaidClient

    if not getattr(user, "plaid_access_token", None):
        return {"created": 0, "skipped": 0, "error": "Plaid not connected"}

    plaid = PlaidClient(user)
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        transactions = plaid.get_transactions(start_date=start, end_date=end, count=count)
    except Exception as e:
        logger.error(f"Failed to fetch Plaid transactions for clustering: {e}")
        return {"created": 0, "skipped": 0, "error": str(e)}

    stream, _ = DataStream.objects.get_or_create(
        user=user,
        source_type="plaid",
        defaults={"payload": {"source": "plaid"}},
    )

    created = 0
    skipped = 0
    for tx in transactions or []:
        tx_id = str(tx.get("transaction_id") or tx.get("id") or "").strip()
        if not tx_id:
            skipped += 1
            continue
        if DocumentChunk.objects.filter(
            stream=stream, metadata__transaction_id=tx_id
        ).exists():
            skipped += 1
            continue

        name = str(tx.get("name") or tx.get("merchant_name") or "Transaction")
        amount = float(tx.get("amount") or 0)
        category = tx.get("category") or tx.get("personal_finance_category") or []
        if isinstance(category, dict):
            category = [
                category.get("primary") or "",
                category.get("detailed") or "",
            ]
        date = str(tx.get("date") or "")
        label = classify_transaction(name, category, amount)
        content = (
            f"Transaction: {name}\n"
            f"Amount: {amount}\n"
            f"Date: {date}\n"
            f"Category: {category}\n"
        ).strip()

        DocumentChunk.objects.create(
            stream=stream,
            content=content,
            cluster_category=label,
            metadata={
                "transaction_id": tx_id,
                "name": name,
                "amount": amount,
                "date": date,
                "category": category,
                "source_type": "plaid",
            },
        )
        created += 1

    return {
        "stream": str(stream.id),
        "created": created,
        "skipped": skipped,
        "total": len(transactions or []),
    }
