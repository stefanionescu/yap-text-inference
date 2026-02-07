"""Tool response validation utilities.

This module provides functions for validating tool call responses from the
server, including JSON parsing and structure validation.
"""

from __future__ import annotations

import json
from typing import Any

from tests.state import TurnResult


def _parse_tool_raw(raw: Any) -> list | None:
    """Parse raw tool response into a list.

    Args:
        raw: The raw response (None, list, or JSON string).

    Returns:
        Parsed list, or None if parsing fails.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip()
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _is_valid_tool_item(item: Any) -> bool:
    """Check if a single tool item has valid structure.

    Args:
        item: A single item from the tool response array.

    Returns:
        True if the item has valid structure.
    """
    if not isinstance(item, dict):
        return False
    return "name" in item and ("arguments" not in item or isinstance(item["arguments"], dict))


def is_valid_response_shape(turn: TurnResult) -> bool:
    """Validate tool response shape.

    Expects a JSON array response where each item has a 'name' field
    and optionally an 'arguments' dict.

    Args:
        turn: The turn result to validate.

    Returns:
        True if the response has a valid shape, False otherwise.
    """
    parsed_list = _parse_tool_raw(turn.tool_raw)
    if parsed_list is None:
        return False

    return all(_is_valid_tool_item(item) for item in parsed_list)


def derive_tool_called_from_raw(raw: Any) -> bool | None:
    """Derive tool_called boolean from raw response by parsing it.

    Args:
        raw: The raw tool response from the server.

    Returns:
        True if non-empty array, False if empty array, None if can't parse.
    """
    parsed_list = _parse_tool_raw(raw)
    if parsed_list is None:
        return None
    return len(parsed_list) > 0


def format_bool(value: bool | None) -> str:
    """Format a boolean value for display."""
    if value is None:
        return "unknown"
    return "yes" if value else "no"


__all__ = [
    "derive_tool_called_from_raw",
    "format_bool",
    "is_valid_response_shape",
]
