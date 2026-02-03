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


def test_telegram_connection() -> Tuple[str, str]:
    """
    Call GET base_url/bot{token}/getMe. Update DB status and return (status, message).
    status is CONNECTION_STATUS_SUCCESS, CONNECTION_STATUS_FAILED, or 'not_configured'.
    """
    creds = get_telegram_credentials_for_test()
    if not creds:
        update_telegram_connection_status("not_configured")
        return ("not_configured", "Token not configured")

    base = (creds["base_url"] or "").strip().rstrip("/")
    token = (creds["access_token"] or "").strip()
    if not token:
        update_telegram_connection_status("not_configured")
        return ("not_configured", "Token not configured")

    url = f"{base}/bot{token}/getMe"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
    except Exception as e:
        logger.warning("Telegram getMe request failed: %s", e)
        update_telegram_connection_status(CONNECTION_STATUS_FAILED)
        return (CONNECTION_STATUS_FAILED, str(e))

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
