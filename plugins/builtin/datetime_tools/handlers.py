"""DateTime plugin handlers."""
from datetime import datetime, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from various formats: YYYY-MM-DD, DD.MM.YYYY, today, tomorrow, yesterday."""
    date_str = date_str.strip().lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str == "today":
        return today
    if date_str == "tomorrow":
        return today + timedelta(days=1)
    if date_str == "yesterday":
        return today - timedelta(days=1)
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


async def get_current_datetime(timezone: Optional[str] = None) -> str:
    """Returns current date and time. Optional timezone (e.g. Europe/Moscow, UTC)."""
    try:
        if timezone and ZoneInfo is not None:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()
        weekday = now.strftime("%A")
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        return f"{formatted} ({weekday})"
    except Exception as e:
        return f"Error: {e}"


async def get_weekday(date: str) -> str:
    """Returns weekday for given date."""
    try:
        parsed = _parse_date(date)
        if parsed is None:
            return f"Error: Cannot parse date '{date}'"
        weekday = parsed.strftime("%A")
        formatted = parsed.strftime("%Y-%m-%d")
        return f"{formatted} is {weekday}"
    except Exception as e:
        return f"Error: {e}"


async def calculate_date_difference(date1: str, date2: str) -> str:
    """Computes difference between two dates in days."""
    try:
        d1 = _parse_date(date1)
        d2 = _parse_date(date2)
        if d1 is None:
            return f"Error: Cannot parse date '{date1}'"
        if d2 is None:
            return f"Error: Cannot parse date '{date2}'"
        diff = abs((d2 - d1).days)
        return f"{diff} days"
    except Exception as e:
        return f"Error: {e}"
