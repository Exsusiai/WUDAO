from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from python.core import crypto
from services.api.config import settings


TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def patch_fernet_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "fernet_key", TEST_KEY)


def test_roundtrip_basic() -> None:
    assert crypto.decrypt(crypto.encrypt("hello")) == "hello"


def test_different_plaintexts_different_ciphertexts() -> None:
    assert crypto.encrypt("abc") != crypto.encrypt("xyz")


def test_same_plaintext_different_ciphertexts() -> None:
    # Fernet uses random IV per call
    assert crypto.encrypt("same") != crypto.encrypt("same")


def test_ciphertext_not_equal_to_plaintext() -> None:
    plaintext = "mysecret"
    assert crypto.encrypt(plaintext) != plaintext


def test_empty_string_roundtrip() -> None:
    assert crypto.decrypt(crypto.encrypt("")) == ""


def test_unicode_roundtrip() -> None:
    text = "悟道交易 🚀 special!@#$%"
    assert crypto.decrypt(crypto.encrypt(text)) == text


def test_missing_fernet_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "fernet_key", "")
    with pytest.raises(ValueError, match="FERNET_KEY is not configured"):
        crypto.encrypt("anything")


def test_wrong_key_raises_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    ciphertext = crypto.encrypt("secret")
    other_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "fernet_key", other_key)
    with pytest.raises(InvalidToken):
        crypto.decrypt(ciphertext)
