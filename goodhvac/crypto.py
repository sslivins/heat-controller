"""Symmetric encryption for device credentials at rest.

Uses Fernet (AES-128-CBC + HMAC) keyed by ``settings.credential_encryption_key``.
Only the device password is encrypted -- usernames aren't secret and are
useful to see/filter on without decrypting.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from goodhvac.config import settings

_fernet = Fernet(settings.credential_encryption_key.encode())


def encrypt_password(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Defensive: a row written under a different key, or legacy
        # plaintext data from before encryption was introduced. Treat as
        # "no usable credential" rather than crashing a poll/apply cycle.
        return None
