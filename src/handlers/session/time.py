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

from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo


@dataclass(frozen=True, slots=True)
class SessionTimestamp:
    """Structured representation of a session timestamp.
    
    Immutable dataclass holding all time-related metadata for a session.
    
    Attributes:
        iso: ISO 8601 formatted timestamp (e.g., "2024-01-15T14:30:00+00:00").
        classification: Human-readable time of day (e.g., "Afternoon").
        display: Combined format for logging (e.g., "2024-01-15T14:30:00+00:00 (Afternoon)").
        tz: Timezone name (e.g., "UTC", "EST").
    """

    iso: str
    classification: str
    display: str
    tz: str


def get_time_classification(hour: int) -> str:
    """Classify time of day based on hour.

    Args:
        hour: Hour in 24-hour format (0-23)

    Returns:
        Time classification string
    """
    if hour == 0:
        return "Midnight"
    if 1 <= hour <= 3:
        return "Night"
    if 4 <= hour <= 6:
        return "Early Morning"
    if 7 <= hour <= 11:
        return "Morning"
    if hour == 12:
        return "Noon"
    if 13 <= hour <= 16:
        return "Afternoon"
    if 17 <= hour <= 20:
        return "Early Evening"
    if 21 <= hour <= 23:
        return "Evening"
    return "Unknown"


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

