"""
Secret encryption helpers.

Credentials stored in the database (currently ``LLMConfiguration.api_key``) are
encrypted at rest with Fernet (symmetric AES-128-CBC + HMAC-SHA256 via the
``cryptography`` package). The encryption key is derived from the
``SECRET_ENCRYPTION_KEY`` setting when provided, otherwise from
``DJANGO_SECRET_KEY``.

Encrypted values are prefixed with ``enc::`` so that:

* plaintext rows written before this feature existed can still be read
  (``decrypt_secret`` passes them through unchanged);
* the model ``save()`` hook can detect and encrypt them lazily;
* a data migration can encrypt legacy rows idempotently.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_PREFIX = "enc::"
logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    secret = getattr(settings, "SECRET_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def is_encrypted(value: str) -> bool:
    return bool(value and value.startswith(_PREFIX))


def encrypt_secret(value: str) -> str:
    """Encrypt a plaintext secret for storage. Empty values stay empty."""
    if not value or is_encrypted(value):
        return value or ""
    return _PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored secret. Plaintext (legacy) values pass through."""
    if not token or not is_encrypted(token):
        return token or ""
    try:
        return _fernet().decrypt(token[len(_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.exception(
            "Failed to decrypt a stored secret. Has SECRET_ENCRYPTION_KEY / "
            "DJANGO_SECRET_KEY changed since it was encrypted?"
        )
        return ""
