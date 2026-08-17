import pytest
from config.security import (
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
)


def test_encrypt_then_decrypt_roundtrip():
    plaintext = "nvapi-super-secret-token-123"
    token = encrypt_secret(plaintext)
    assert token != plaintext
    assert is_encrypted(token)
    assert token.startswith("enc::")
    assert decrypt_secret(token) == plaintext


def test_empty_and_legacy_plaintext_pass_through():
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""
    assert not is_encrypted("")
    # Legacy plaintext rows are readable and flagged as not encrypted.
    assert decrypt_secret("plaintext-old-row") == "plaintext-old-row"
    assert not is_encrypted("plaintext-old-row")


def test_encrypt_is_idempotent():
    token = encrypt_secret("abc")
    assert encrypt_secret(token) == token


def test_decrypt_returns_empty_on_tampered_token():
    tampered = "enc::" + "A" * 100
    assert decrypt_secret(tampered) == ""


@pytest.mark.django_db
def test_llm_configuration_saves_encrypted_and_decrypts(user):
    from apps.integrations.models import LLMConfiguration

    config = LLMConfiguration.objects.create(
        user=user,
        provider="nvidia",
        name="Test NIM",
        api_key="plaintext-secret",
        model_name="meta/llama-3.1-8b-instruct",
    )
    config.refresh_from_db()
    assert config.api_key.startswith("enc::")
    assert "plaintext-secret" not in config.api_key
    assert config.decrypted_api_key == "plaintext-secret"
