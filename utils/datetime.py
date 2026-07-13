from datetime import datetime, timezone
from zoneinfo import ZoneInfo


TASHKENT_TIMEZONE = ZoneInfo("Asia/Tashkent")
LOCAL_DATETIME_FORMAT = "%d.%m.%Y %H:%M"


def parse_datetime(value: datetime | str) -> datetime:
    """Parse backend timestamps and normalize them to an aware UTC datetime."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        parsed = datetime.fromisoformat(normalized)
    else:
        raise TypeError("datetime value must be a datetime or ISO-8601 string")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def to_tashkent(value: datetime | str) -> datetime:
    """Convert a backend UTC timestamp to Asia/Tashkent."""
    return parse_datetime(value).astimezone(TASHKENT_TIMEZONE)


def format_tashkent_datetime(value: datetime | str | None, default: str = "—") -> str:
    """Return local date/time without a timezone suffix for bot messages."""
    if value in (None, ""):
        return default

    try:
        return to_tashkent(value).strftime(LOCAL_DATETIME_FORMAT)
    except (TypeError, ValueError):
        return default
