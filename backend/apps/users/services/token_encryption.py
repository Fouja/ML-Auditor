"""
OAuth token encryption at rest.
Encrypts tokens before storing in database.
"""

import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_key() -> bytes:
    """Derive encryption key from Django secret key."""
    secret = settings.SECRET_KEY.encode()
    return base64.urlsafe_b64encode(hashlib.sha256(secret).digest())


_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_key())
    return _fernet


def encrypt_token(token: str) -> str:
    """Encrypt a token string for storage."""
    if not token:
        return token
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token."""
    if not encrypted:
        return encrypted
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def encrypt_user_tokens(user) -> None:
    """Encrypt all OAuth tokens on a user model."""
    fields = [
        "google_access_token", "google_refresh_token",
        "plaid_access_token",
        "canva_access_token", "canva_refresh_token",
        "email_imap_password",
    ]
    for field in fields:
        val = getattr(user, field, None)
        if val and not val.startswith("enc:"):
            encrypted = encrypt_token(val)
            setattr(user, field, f"enc:{encrypted}")
    user.save()


def decrypt_user_token(user, field: str) -> str:
    """Decrypt a specific user token field."""
    val = getattr(user, field, None)
    if not val:
        return val
    if val.startswith("enc:"):
        return decrypt_token(val[4:])
    return val
