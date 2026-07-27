"""
Input validation and XSS prevention utilities.
"""

import html
import re
from typing import Any

# Allowed HTML tags for rich content (minimal safe set)
ALLOWED_TAGS = {"b", "i", "u", "em", "strong", "p", "br", "ul", "ol", "li", "a", "span"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "span": {"class"}}


def sanitize_html(text: str) -> str:
    """Strip all HTML tags and escape entities."""
    text = re.sub(r"<[^>]+>", "", text)
    return html.escape(text)


def sanitize_input(data: Any) -> Any:
    """Recursively sanitize all string values in a dict/list."""
    if isinstance(data, str):
        return sanitize_html(data.strip())
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(pattern, value, re.IGNORECASE))


def truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to max length, escaping HTML."""
    text = sanitize_html(text)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
