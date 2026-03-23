"""Time and duration helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_duration(total_seconds: float) -> str:
    seconds = max(int(total_seconds), 0)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_timestamp(moment: datetime | None) -> str:
    if moment is None:
        return "Unavailable"
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
