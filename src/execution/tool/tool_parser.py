"""Tool result parsing utilities."""

import json
from typing import Any


def parse_tool_result(tool_result: dict | None) -> tuple[Any, bool]:
    """Parse tool result into raw field and boolean decision.
    
    Args:
        tool_result: Tool execution result dict
        
    Returns:
        Tuple of (raw_field, is_tool)
    """
    raw_field = None
    is_tool = False
    
    raw_txt = (tool_result or {}).get("text") if tool_result else None
    
    if isinstance(raw_txt, str):
        raw_stripped = raw_txt.strip()
        if raw_stripped:
            if raw_stripped.startswith("["):
                try:
                    parsed = json.loads(raw_stripped)
                    if isinstance(parsed, list):
                        raw_field = parsed
                        is_tool = len(parsed) > 0
                    else:
                        raw_field = raw_stripped
                except Exception:
                    raw_field = raw_stripped
                    is_tool = raw_stripped != "[]"
            else:
                raw_field = raw_stripped
                is_tool = False
    
    return raw_field, is_tool
