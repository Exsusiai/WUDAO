from __future__ import annotations

from cryptography.fernet import Fernet

from services.api.config import settings


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext string, return base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt base64-encoded ciphertext, return plaintext string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def _get_fernet() -> Fernet:
    if not settings.fernet_key:
        raise ValueError("FERNET_KEY is not configured")
    return Fernet(settings.fernet_key.encode())
