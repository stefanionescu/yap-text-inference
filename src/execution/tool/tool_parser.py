"""Tool result parsing utilities."""

import json
from typing import Any


def _extract_json_array(text: str) -> list | None:
    """Extract a JSON array from text, handling trailing content like explanations.
    
    Handles formats like:
    - '[{"name": "take_screenshot"}]. REASON FOR CHOOSING THIS: ...'
    - '[]. REASON FOR CHOOSING THIS: ...'
    - '[]'
    - '[{"name": "take_screenshot"}]'
    
    Args:
        text: Input text that may contain a JSON array followed by other content
        
    Returns:
        Parsed list if valid JSON array found, None otherwise
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text.startswith("["):
        return None
    
    # Try to find the closing bracket of the JSON array
    # This handles cases where there's extra text after the JSON (e.g., explanations)
    bracket_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1
            if bracket_count == 0:
                # Found the end of the JSON array
                try:
                    parsed = json.loads(text[:i + 1])
                    if isinstance(parsed, list):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
                return None
    return None


def parse_tool_result(tool_result: dict | None) -> tuple[Any, bool]:
    """Parse tool result into raw field and boolean decision.
    
    Handles responses that may include explanations after the JSON array, e.g.:
    '[{"name": "take_screenshot"}]. REASON FOR CHOOSING THIS: ...'
    '[]. REASON FOR CHOOSING THIS: ...'
    
    Args:
        tool_result: Tool execution result dict
        
    Returns:
        Tuple of (raw_field, is_tool)
    """
    raw_field = None
    is_tool = False
    
    raw_txt = (tool_result or {}).get("text") if tool_result else None
    
    if isinstance(raw_txt, str):
        # Normalize newlines and whitespace (handles cases like "[].\nREASON")
        normalized = raw_txt.replace("\n", " ").replace("\r", " ").strip()
        if normalized:
            if normalized.startswith("["):
                # Try to extract JSON array (handles trailing explanations)
                parsed_list = _extract_json_array(normalized)
                if parsed_list is not None:
                    raw_field = parsed_list
                    is_tool = len(parsed_list) > 0
                else:
                    # Fallback: try parsing entire normalized string
                    try:
                        parsed = json.loads(normalized)
                        if isinstance(parsed, list):
                            raw_field = parsed
                            is_tool = len(parsed) > 0
                        else:
                            raw_field = normalized
                            is_tool = False
                    except (json.JSONDecodeError, ValueError):
                        # If parsing fails completely, check if it starts with empty array
                        # This handles malformed responses - be conservative
                        if normalized.startswith("[]"):
                            # Likely empty array with trailing text
                            raw_field = []
                            is_tool = False
                        else:
                            raw_field = normalized
                            is_tool = False
            else:
                raw_field = normalized
                is_tool = False
    
    return raw_field, is_tool
