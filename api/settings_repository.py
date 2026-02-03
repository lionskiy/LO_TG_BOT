"""Load and save Telegram and LLM settings; mask secrets for API responses."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from api.db import (
    CONNECTION_STATUS_NOT_CONFIGURED,
    LLMSettingsModel,
    SessionLocal,
    TelegramSettingsModel,
)
from api.encryption import decrypt_secret, encrypt_secret

MASK_TAIL_LEN = 5
TELEGRAM_DEFAULT_BASE_URL = "https://api.telegram.org"


def mask_secret(value: Optional[str]) -> str:
    """Return masked string (last MASK_TAIL_LEN chars visible) for API."""
    if not value or len(value.strip()) == 0:
        return ""
    s = value.strip()
    if len(s) <= MASK_TAIL_LEN:
        return "****"
    return "..." + s[-MASK_TAIL_LEN:]


def _telegram_row(session: Session) -> Optional[TelegramSettingsModel]:
    return session.query(TelegramSettingsModel).first()


def _llm_row(session: Session) -> Optional[LLMSettingsModel]:
    return session.query(LLMSettingsModel).first()


def get_telegram_settings() -> dict[str, Any]:
    """Return Telegram settings for API (masked token)."""
    with SessionLocal() as session:
        row = _telegram_row(session)
        if not row:
            return {
                "accessToken": None,
                "accessTokenMasked": "",
                "baseUrl": TELEGRAM_DEFAULT_BASE_URL,
                "connectionStatus": CONNECTION_STATUS_NOT_CONFIGURED,
                "isActive": False,
                "lastActivatedAt": None,
                "lastChecked": None,
            }
        token_plain = decrypt_secret(row.access_token_encrypted) if row.access_token_encrypted else None
        return {
            "accessToken": None,
            "accessTokenMasked": mask_secret(token_plain),
            "baseUrl": row.base_url or TELEGRAM_DEFAULT_BASE_URL,
            "connectionStatus": row.connection_status,
            "isActive": row.is_active,
            "lastActivatedAt": row.last_activated_at.isoformat() if row.last_activated_at else None,
            "lastChecked": row.last_checked.isoformat() if row.last_checked else None,
        }


def get_telegram_settings_decrypted() -> Optional[dict]:
    """Return Telegram settings with decrypted token for internal use (bot)."""
    with SessionLocal() as session:
        row = _telegram_row(session)
        if not row or not row.is_active or not row.access_token_encrypted:
            return None
        token = decrypt_secret(row.access_token_encrypted)
        if not token:
            return None
        return {
            "access_token": token,
            "base_url": row.base_url or TELEGRAM_DEFAULT_BASE_URL,
        }


def save_telegram_settings(
    access_token: Optional[str],
    base_url: Optional[str],
    connection_status: str,
    is_active: bool = False,
) -> dict[str, Any]:
    """Save Telegram block. Empty base_url replaced with default. Returns API-shaped dict."""
    base_url = (base_url or "").strip() or TELEGRAM_DEFAULT_BASE_URL
    encrypted = encrypt_secret(access_token) if access_token else None

    with SessionLocal() as session:
        row = _telegram_row(session)
        now = datetime.utcnow()
        if row:
            row.access_token_encrypted = encrypted
            row.base_url = base_url
            row.connection_status = connection_status
            row.is_active = is_active
            if is_active:
                row.last_activated_at = now
            row.last_checked = now
            row.updated_at = now
        else:
            row = TelegramSettingsModel(
                access_token_encrypted=encrypted,
                base_url=base_url,
                connection_status=connection_status,
                is_active=is_active,
                last_activated_at=now if is_active else None,
                last_checked=now,
            )
            session.add(row)
        session.commit()
        session.refresh(row)

    token_plain = decrypt_secret(row.access_token_encrypted) if row.access_token_encrypted else None
    return {
        "accessToken": None,
        "accessTokenMasked": mask_secret(token_plain),
        "baseUrl": row.base_url,
        "connectionStatus": row.connection_status,
        "isActive": row.is_active,
        "lastActivatedAt": row.last_activated_at.isoformat() if row.last_activated_at else None,
        "lastChecked": row.last_checked.isoformat() if row.last_checked else None,
    }


def get_llm_settings() -> dict[str, Any]:
    """Return LLM settings for API (masked API key)."""
    with SessionLocal() as session:
        row = _llm_row(session)
        if not row:
            return {
                "llmType": None,
                "apiKey": None,
                "apiKeyMasked": "",
                "baseUrl": "",
                "modelType": "",
                "systemPrompt": None,
                "connectionStatus": CONNECTION_STATUS_NOT_CONFIGURED,
                "isActive": False,
                "lastActivatedAt": None,
                "lastChecked": None,
            }
        key_plain = decrypt_secret(row.api_key_encrypted) if row.api_key_encrypted else None
        return {
            "llmType": row.llm_type,
            "apiKey": None,
            "apiKeyMasked": mask_secret(key_plain),
            "baseUrl": row.base_url,
            "modelType": row.model_type,
            "systemPrompt": row.system_prompt or None,
            "connectionStatus": row.connection_status,
            "isActive": row.is_active,
            "lastActivatedAt": row.last_activated_at.isoformat() if row.last_activated_at else None,
            "lastChecked": row.last_checked.isoformat() if row.last_checked else None,
        }


def get_llm_settings_decrypted() -> Optional[dict]:
    """Return LLM settings with decrypted API key for internal use (get_reply)."""
    with SessionLocal() as session:
        row = _llm_row(session)
        if not row or not row.is_active:
            return None
        key = decrypt_secret(row.api_key_encrypted) if row.api_key_encrypted else None
        if not key and row.llm_type != "ollama":
            return None
        return {
            "llm_type": row.llm_type,
            "api_key": key or "ollama",
            "base_url": row.base_url,
            "model_type": row.model_type,
            "system_prompt": row.system_prompt or None,
        }


def save_llm_settings(
    llm_type: str,
    api_key: Optional[str],
    base_url: str,
    model_type: str,
    system_prompt: Optional[str],
    connection_status: str,
    is_active: bool = False,
) -> dict[str, Any]:
    """Save LLM block. Returns API-shaped dict."""
    encrypted = encrypt_secret(api_key) if api_key else None

    with SessionLocal() as session:
        row = _llm_row(session)
        now = datetime.utcnow()
        if row:
            row.llm_type = llm_type
            row.api_key_encrypted = encrypted
            row.base_url = base_url
            row.model_type = model_type
            row.system_prompt = (system_prompt or "").strip() or None
            row.connection_status = connection_status
            row.is_active = is_active
            if is_active:
                row.last_activated_at = now
            row.last_checked = now
            row.updated_at = now
        else:
            row = LLMSettingsModel(
                llm_type=llm_type,
                api_key_encrypted=encrypted,
                base_url=base_url,
                model_type=model_type,
                system_prompt=(system_prompt or "").strip() or None,
                connection_status=connection_status,
                is_active=is_active,
                last_activated_at=now if is_active else None,
                last_checked=now,
            )
            session.add(row)
        session.commit()
        session.refresh(row)

    key_plain = decrypt_secret(row.api_key_encrypted) if row.api_key_encrypted else None
    return {
        "llmType": row.llm_type,
        "apiKey": None,
        "apiKeyMasked": mask_secret(key_plain),
        "baseUrl": row.base_url,
        "modelType": row.model_type,
        "systemPrompt": row.system_prompt,
        "connectionStatus": row.connection_status,
        "isActive": row.is_active,
        "lastActivatedAt": row.last_activated_at.isoformat() if row.last_activated_at else None,
        "lastChecked": row.last_checked.isoformat() if row.last_checked else None,
    }


def update_telegram_connection_status(status: str, last_checked: Optional[datetime] = None) -> None:
    """Update only connection_status and last_checked for Telegram."""
    with SessionLocal() as session:
        row = _telegram_row(session)
        if row:
            row.connection_status = status
            row.last_checked = last_checked or datetime.utcnow()
            session.commit()


def update_llm_connection_status(status: str, last_checked: Optional[datetime] = None) -> None:
    """Update only connection_status and last_checked for LLM."""
    with SessionLocal() as session:
        row = _llm_row(session)
        if row:
            row.connection_status = status
            row.last_checked = last_checked or datetime.utcnow()
            session.commit()


def set_telegram_active(active: bool) -> None:
    """Set is_active and last_activated_at for Telegram."""
    with SessionLocal() as session:
        row = _telegram_row(session)
        if row:
            row.is_active = active
            row.last_activated_at = datetime.utcnow() if active else None
            session.commit()


def set_llm_active(active: bool) -> None:
    """Set is_active and last_activated_at for LLM."""
    with SessionLocal() as session:
        row = _llm_row(session)
        if row:
            row.is_active = active
            row.last_activated_at = datetime.utcnow() if active else None
            session.commit()
