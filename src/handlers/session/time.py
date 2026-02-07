"""Time classification and formatting utilities.

This module provides utilities for working with timestamps in session metadata.
It generates structured timestamp information that includes:

- ISO 8601 formatted time
- Human-readable classification (Morning, Afternoon, Evening, etc.)
- Display string combining ISO and classification
- Timezone name

The classification allows prompts to reference time of day naturally,
e.g., "Good morning" vs "Good evening" in system prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo

from src.state import SessionTimestamp

HOUR_MIDNIGHT = 0
NIGHT_START = 1
NIGHT_END = 3
EARLY_MORNING_START = 4
EARLY_MORNING_END = 6
MORNING_START = 7
MORNING_END = 11
HOUR_NOON = 12
AFTERNOON_START = 13
AFTERNOON_END = 16
EARLY_EVENING_START = 17
EARLY_EVENING_END = 20
EVENING_START = 21
EVENING_END = 23


def get_time_classification(hour: int) -> str:
    """Classify time of day based on hour.

    Args:
        hour: Hour in 24-hour format (0-23)

    Returns:
        Time classification string
    """
    classification = "Unknown"
    if hour == HOUR_MIDNIGHT:
        classification = "Midnight"
    elif NIGHT_START <= hour <= NIGHT_END:
        classification = "Night"
    elif EARLY_MORNING_START <= hour <= EARLY_MORNING_END:
        classification = "Early Morning"
    elif MORNING_START <= hour <= MORNING_END:
        classification = "Morning"
    elif hour == HOUR_NOON:
        classification = "Noon"
    elif AFTERNOON_START <= hour <= AFTERNOON_END:
        classification = "Afternoon"
    elif EARLY_EVENING_START <= hour <= EARLY_EVENING_END:
        classification = "Early Evening"
    elif EVENING_START <= hour <= EVENING_END:
        classification = "Evening"
    return classification


def format_session_timestamp(
    *,
    now: datetime | None = None,
    tz: tzinfo | None = None,
) -> SessionTimestamp:
    """Generate a timezone-aware timestamp for session metadata.

    Args:
        now: Optional datetime to format (useful for tests).  Defaults to current UTC time.
        tz: Target timezone. Defaults to UTC.

    Returns:
        SessionTimestamp: Structured timestamp with ISO, classification, and human display value.
    """

    target_tz = tz or timezone.utc
    current = now or datetime.now(tz=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    localized = current.astimezone(target_tz)

    classification = get_time_classification(localized.hour)
    iso_value = localized.replace(microsecond=0).isoformat()

    return SessionTimestamp(
        iso=iso_value,
        classification=classification,
        display=f"{iso_value} ({classification})",
        tz=localized.tzname() or str(target_tz),
    )


__all__ = ["SessionTimestamp", "get_time_classification", "format_session_timestamp"]
