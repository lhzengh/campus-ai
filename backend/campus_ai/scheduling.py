"""Provide timezone-safe calculations for source collection schedules."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone(value: str) -> str:
    """Return a valid IANA timezone name or raise a user-facing error."""

    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone: {value}") from exc
    return value


def as_utc(value: datetime) -> datetime:
    """Normalize database timestamps, including SQLite's naive UTC values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def next_daily_run(schedule_time: time, timezone_name: str, *, after: datetime) -> datetime:
    """Calculate the first daily execution strictly after the supplied instant."""

    zone = ZoneInfo(validate_timezone(timezone_name))
    local_after = as_utc(after).astimezone(zone)
    candidate = datetime.combine(local_after.date(), schedule_time, tzinfo=zone)
    if candidate <= local_after:
        candidate = datetime.combine(local_after.date() + timedelta(days=1), schedule_time, tzinfo=zone)
    return candidate.astimezone(timezone.utc)
