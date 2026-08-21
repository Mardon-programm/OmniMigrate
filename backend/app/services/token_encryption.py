"""Token encryption service — encrypts/decrypts sensitive values (GitHub tokens) using Fernet."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plaintext: str) -> str:
    f = Fernet(_derive_key(settings.secret_key))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    f = Fernet(_derive_key(settings.secret_key))
    return f.decrypt(ciphertext.encode()).decode()
