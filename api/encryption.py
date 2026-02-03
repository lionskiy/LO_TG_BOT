"""Encrypt/decrypt sensitive settings (tokens, API keys) for DB storage."""
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

_ENCRYPTION_KEY_ENV = "SETTINGS_ENCRYPTION_KEY"
_ENCRYPTION_KEY_FILE_ENV = "SETTINGS_ENCRYPTION_KEY_FILE"
_DEFAULT_KEY_FILE = _PROJECT_ROOT / "data" / ".encryption_key"
logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _key_file_path() -> Path:
    """Path to auto-generated key file (in data volume in Docker)."""
    p = os.getenv(_ENCRYPTION_KEY_FILE_ENV)
    if p and p.strip():
        return Path(p.strip())
    return _DEFAULT_KEY_FILE


def _get_or_create_key_from_file() -> bytes:
    """Read key from file; if file missing, generate key, write to file, return it."""
    path = _key_file_path()
    if path.exists():
        raw = path.read_bytes().strip()
        if raw:
            return raw
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    logger.info("Generated and saved encryption key to %s", path)
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    raw = os.getenv(_ENCRYPTION_KEY_ENV)
    if raw and raw.strip():
        key = raw.strip().encode() if isinstance(raw, str) else raw
    else:
        key = _get_or_create_key_from_file()
    try:
        _fernet = Fernet(key)
    except Exception as e:
        raise ValueError(f"Invalid encryption key: {e}") from e
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
