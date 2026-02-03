"""Test Telegram Bot API connection (getMe)."""
import logging
from typing import Tuple

import httpx

from api.db import CONNECTION_STATUS_FAILED, CONNECTION_STATUS_SUCCESS
from api.settings_repository import (
    get_telegram_credentials_for_test,
    update_telegram_connection_status,
)

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


def _check_telegram_response(r: httpx.Response) -> Tuple[str, str]:
    """Parse response and return (status, message). Updates DB status."""
    try:
        data = r.json()
    except Exception as e:
        update_telegram_connection_status(CONNECTION_STATUS_FAILED)
        return (CONNECTION_STATUS_FAILED, f"Invalid response: {e}")
    if r.status_code == 200 and data.get("ok") is True:
        update_telegram_connection_status(CONNECTION_STATUS_SUCCESS)
        return (CONNECTION_STATUS_SUCCESS, "Connection tested successfully")
    update_telegram_connection_status(CONNECTION_STATUS_FAILED)
    msg = data.get("description", data.get("error", r.text)) if isinstance(data, dict) else r.text
    return (CONNECTION_STATUS_FAILED, msg or f"HTTP {r.status_code}")


def _get_creds_or_not_configured() -> Tuple[bool, str, str]:
    """Get creds; on ValueError (missing key) return not_configured. Returns (ok, status, message)."""
    try:
        creds = get_telegram_credentials_for_test()
    except ValueError:
        update_telegram_connection_status("not_configured")
        return (False, "not_configured", "SETTINGS_ENCRYPTION_KEY is not set")
    if not creds:
        update_telegram_connection_status("not_configured")
        return (False, "not_configured", "Token not configured")
    base = (creds["base_url"] or "").strip().rstrip("/")
    token = (creds["access_token"] or "").strip()
    if not token:
        update_telegram_connection_status("not_configured")
        return (False, "not_configured", "Token not configured")
    return (True, base, token)


def test_telegram_connection() -> Tuple[str, str]:
    """
    Call GET base_url/bot{token}/getMe. Update DB status and return (status, message).
    Blocking (sync). Use test_telegram_connection_async for HTTP endpoint to avoid blocking.
    """
    ok, a, b = _get_creds_or_not_configured()
    if not ok:
        return (a, b)
    base, token = a, b
    url = f"{base}/bot{token}/getMe"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(url)
    except Exception as e:
        logger.warning("Telegram getMe request failed: %s", e)
        update_telegram_connection_status(CONNECTION_STATUS_FAILED)
        return (CONNECTION_STATUS_FAILED, str(e))
    return _check_telegram_response(r)


async def test_telegram_connection_async() -> Tuple[str, str]:
    """
    Async: call GET base_url/bot{token}/getMe. Does not block the event loop.
    Use for POST /api/settings/telegram/test to avoid freezing the UI.
    """
    ok, a, b = _get_creds_or_not_configured()
    if not ok:
        return (a, b)
    base, token = a, b
    url = f"{base}/bot{token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
    except Exception as e:
        logger.warning("Telegram getMe request failed: %s", e)
        update_telegram_connection_status(CONNECTION_STATUS_FAILED)
        return (CONNECTION_STATUS_FAILED, str(e))
    return _check_telegram_response(r)
