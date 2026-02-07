"""Tool result parsing utilities.

This module parses the JSON output from the tool classifier into structured
results for the execution pipeline. The classifier returns JSON arrays like:

    '[{"name": "take_screenshot"}]'  -> Tool call requested
    '[]'                              -> No tool call

Edge Case Handling:
    - Strips markdown code fences (```json ... ```)
    - Handles trailing code fence artifacts
    - Gracefully handles malformed JSON
    - Returns (None, False) for cancelled/empty results
"""

import json
import re
from typing import Any


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from text.

    Handles cases like:
    - '[]\n```' -> '[]'
    - '```json\n[]\n```' -> '[]'
    - '```\n[]\n```' -> '[]'
    - '[]```' -> '[]'
    - '[{"name": "take_screenshot"}]\n```' -> '[{"name": "take_screenshot"}]'
    """
    # Remove leading/trailing whitespace first
    text = text.strip()

    # Remove leading code fence: ``` optionally followed by language identifier
    # Match: ``` (optional language like json/python/etc) followed by optional whitespace/newlines
    text = re.sub(r"^```[a-zA-Z]*\s*\n*", "", text, flags=re.MULTILINE)

    # Remove trailing code fence: optional whitespace/newlines followed by ```
    # This handles cases like '[]\n```' or '[]```' or '\n```'
    text = re.sub(r"\s*\n*```\s*$", "", text, flags=re.MULTILINE)

    # Final cleanup: remove any remaining trailing ``` that might be stuck
    text = re.sub(r"```\s*$", "", text)

    return text.strip()


def parse_tool_result(tool_result: dict | None) -> tuple[Any, bool]:
    """Parse tool result into raw field and boolean decision.

    Expects the tool to return a JSON array:
    - '[{"name": "take_screenshot"}]' -> tool call requested
    - '[]' -> no tool call

    Handles edge cases where LLM adds markdown code fences or extra formatting.

    Args:
        tool_result: Tool execution result dict

    Returns:
        Tuple of (raw_field, is_tool)
        - raw_field: Parsed list or None
        - is_tool: Boolean indicating if tool should be called
    """
    raw_field = None
    is_tool = False

    raw_txt = (tool_result or {}).get("text") if tool_result else None

    if isinstance(raw_txt, str):
        # Strip code fences and normalize whitespace
        normalized = _strip_code_fences(raw_txt)

        if normalized:
            try:
                parsed = json.loads(normalized)
                if isinstance(parsed, list):
                    raw_field = parsed
                    is_tool = len(parsed) > 0
            except (json.JSONDecodeError, ValueError):
                # Invalid JSON - return as-is for debugging
                raw_field = normalized
                is_tool = False

    return raw_field, is_tool


__all__ = ["parse_tool_result"]
