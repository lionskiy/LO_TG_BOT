"""Start/stop/restart Telegram bot subprocess (uses active settings from DB)."""
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_process = None
_project_root = Path(__file__).resolve().parent.parent
_script = _project_root / "run_bot_from_settings.py"


def start_bot() -> None:
    """Start bot subprocess if run_bot_from_settings.py exists and we have env to read DB."""
    global _process
    if _process is not None and _process.poll() is None:
        return
    if not _script.exists():
        logger.debug("run_bot_from_settings.py not found, skipping bot start")
        return
    env = os.environ.copy()
    if "DATABASE_URL" not in env:
        env.setdefault("DATABASE_URL", "sqlite:///./data/settings.db")
    if "SETTINGS_ENCRYPTION_KEY" not in env:
        logger.warning("SETTINGS_ENCRYPTION_KEY not set; bot subprocess may not read DB")
    try:
        _process = subprocess.Popen(
            [sys.executable, str(_script)],
            cwd=str(_project_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        logger.info("Started bot subprocess pid=%s", _process.pid)
    except Exception as e:
        logger.exception("Failed to start bot subprocess: %s", e)


def stop_bot() -> None:
    """Stop bot subprocess if running."""
    global _process
    if _process is None:
        return
    if _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()
        logger.info("Stopped bot subprocess")
    _process = None


def restart_bot() -> None:
    """Stop and start bot subprocess (e.g. after activating new Telegram settings)."""
    stop_bot()
    start_bot()
