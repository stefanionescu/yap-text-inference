"""Unit tests for time classification and session timestamp formatting."""

from __future__ import annotations

from datetime import datetime, timezone

from src.handlers.session.time import get_time_classification, format_session_timestamp

# --- get_time_classification ---


def test_hour_0_midnight() -> None:
    assert get_time_classification(0) == "Midnight"


def test_hour_2_night() -> None:
    assert get_time_classification(2) == "Night"


def test_hour_5_early_morning() -> None:
    assert get_time_classification(5) == "Early Morning"


def test_hour_9_morning() -> None:
    assert get_time_classification(9) == "Morning"


def test_hour_12_noon() -> None:
    assert get_time_classification(12) == "Noon"


def test_hour_14_afternoon() -> None:
    assert get_time_classification(14) == "Afternoon"


def test_hour_18_early_evening() -> None:
    assert get_time_classification(18) == "Early Evening"


def test_hour_22_evening() -> None:
    assert get_time_classification(22) == "Evening"


def test_hour_negative_unknown() -> None:
    assert get_time_classification(-1) == "Unknown"


def test_hour_24_unknown() -> None:
    assert get_time_classification(24) == "Unknown"


# --- format_session_timestamp ---


def test_format_session_timestamp_afternoon() -> None:
    ts = format_session_timestamp(
        now=datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),  # noqa: UP017
        tz=timezone.utc,  # noqa: UP017
    )
    assert ts.classification == "Afternoon"
    assert "14:30" in ts.iso
    assert ts.classification in ts.display


def test_format_session_timestamp_fields() -> None:
    ts = format_session_timestamp(
        now=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),  # noqa: UP017
        tz=timezone.utc,  # noqa: UP017
    )
    assert ts.iso is not None
    assert ts.classification == "Midnight"
    assert ts.display is not None
    assert ts.tz == "UTC"
