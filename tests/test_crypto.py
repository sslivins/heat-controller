"""Credential encryption at rest (Fernet)."""

from __future__ import annotations

from goodhvac.crypto import decrypt_password, encrypt_password


def test_encrypt_decrypt_roundtrip():
    ciphertext = encrypt_password("hunter2")
    assert ciphertext is not None
    assert ciphertext != "hunter2"
    assert decrypt_password(ciphertext) == "hunter2"


def test_encrypt_none_returns_none():
    assert encrypt_password(None) is None


def test_decrypt_none_returns_none():
    assert decrypt_password(None) is None


def test_decrypt_invalid_token_returns_none():
    """Legacy plaintext or a key mismatch should degrade gracefully, not raise."""
    assert decrypt_password("not-a-valid-fernet-token") is None
