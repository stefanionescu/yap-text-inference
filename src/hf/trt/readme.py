"""README template renderer for TRT-LLM models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def render_trt_readme(metadata: dict[str, Any]) -> str:
    """Render the TRT README template with metadata.

    Args:
        metadata: Dictionary of template variables.

    Returns:
        Rendered README content.
    """
    # Load template from the quantization TRT readme module
    src_root = Path(__file__).parent.parent.parent
    template_path = src_root / "quantization" / "trt" / "readme" / "trt_chat_template.md"
    template = template_path.read_text(encoding="utf-8")

    # Simple mustache-style replacement: {{key}} -> value
    def replace_var(match: re.Match) -> str:
        key = match.group(1)
        value = metadata.get(key, "")
        return str(value) if value else ""

    rendered = re.sub(r"\{\{(\w+)\}\}", replace_var, template)

    # Also handle {{key:+ suffix}} syntax (add suffix if key exists)
    def replace_conditional(match: re.Match) -> str:
        key = match.group(1)
        suffix = match.group(2)
        value = metadata.get(key, "")
        return suffix if value else ""

    rendered = re.sub(r"\{\{(\w+):\+([^}]+)\}\}", replace_conditional, rendered)

    return rendered


__all__ = ["render_trt_readme"]
