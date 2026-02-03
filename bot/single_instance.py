"""Один экземпляр бота: при старте завершаем предыдущий процесс, при остановке — снимаем lock."""
import atexit
import logging
import os
import signal
import time
from pathlib import Path
from typing import Optional

PID_FILE = Path(__file__).resolve().parent.parent / ".bot.pid"
logger = logging.getLogger(__name__)


def _read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        data = PID_FILE.read_text().strip()
        return int(data) if data else None
    except (ValueError, OSError):
        return None


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_process(pid: int) -> None:
    if pid <= 0 or pid == os.getpid():
        return
    if not _process_exists(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            if not _process_exists(pid):
                return
        os.kill(pid, signal.SIGKILL)
        logger.warning("Killed stale bot process pid=%s (SIGKILL)", pid)
    except OSError as e:
        logger.debug("Could not kill pid=%s: %s", pid, e)


def _remove_pid_file() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
            logger.debug("Removed PID file %s", PID_FILE)
    except OSError as e:
        logger.debug("Could not remove PID file: %s", e)


def ensure_single_instance() -> None:
    """Завершить другой запущенный экземпляр (по PID в .bot.pid), записать свой PID."""
    existing = _read_pid()
    if existing is not None and existing != os.getpid():
        if _process_exists(existing):
            logger.info("Stopping previous bot instance pid=%s", existing)
            _kill_process(existing)
        _remove_pid_file()
    try:
        PID_FILE.write_text(str(os.getpid()))
    except OSError as e:
        logger.warning("Could not write PID file: %s", e)


def register_cleanup() -> None:
    """При выходе процесса удалить .bot.pid, чтобы не блокировать следующий запуск."""
    atexit.register(_remove_pid_file)

    def _signal_handler(signum: int, frame: object) -> None:
        _remove_pid_file()
        raise SystemExit(0)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _signal_handler)
        except (ValueError, OSError):
            pass
