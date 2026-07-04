from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return an aware UTC timestamp for persistence and comparisons."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize legacy naive timestamps as UTC during migration."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
