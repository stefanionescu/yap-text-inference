"""Tool result parsing utilities."""

import json
from typing import Any


def parse_tool_result(tool_result: dict | None) -> tuple[Any, bool]:
    """Parse tool result into raw field and boolean decision.
    
    Expects the tool to return a JSON array:
    - '[{"name": "take_screenshot"}]' -> tool call requested
    - '[]' -> no tool call
    
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
        normalized = raw_txt.strip()
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
