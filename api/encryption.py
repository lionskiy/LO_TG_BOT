"""Encrypt/decrypt sensitive settings (tokens, API keys) for DB storage."""
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_ENCRYPTION_KEY_ENV = "SETTINGS_ENCRYPTION_KEY"
logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    raw = os.getenv(_ENCRYPTION_KEY_ENV)
    if not raw or len(raw.strip()) == 0:
        raise ValueError(
            f"{_ENCRYPTION_KEY_ENV} is not set. "
            "Generate a key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    key = raw.strip().encode() if isinstance(raw, str) else raw
    try:
        _fernet = Fernet(key)
    except Exception as e:
        raise ValueError(f"Invalid {_ENCRYPTION_KEY_ENV}: {e}") from e
    return _fernet


def encrypt_secret(plain: str) -> Optional[str]:
    """Encrypt a string for DB storage. Returns None for empty input."""
    if not plain or not plain.strip():
        return None
    try:
        return _get_fernet().encrypt(plain.strip().encode("utf-8")).decode("ascii")
    except InvalidToken:
        raise
    except Exception as e:
        logger.exception("Encryption failed: %s", e)
        raise


def decrypt_secret(encrypted: Optional[str]) -> Optional[str]:
    """Decrypt a string from DB. Returns None for empty/None input."""
    if not encrypted or not encrypted.strip():
        return None
    try:
        return _get_fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Decryption failed (invalid token)")
        return None
    except Exception as e:
        logger.exception("Decryption failed: %s", e)
        return None
