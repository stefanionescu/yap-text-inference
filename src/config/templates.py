"""Template and license configuration for AWQ README generation."""

from __future__ import annotations

from typing import Dict


CHAT_TEMPLATE_NAME = "awq_chat_template.md"
TOOL_TEMPLATE_NAME = "awq_tool_template.md"


def resolve_template_name(is_tool: bool) -> str:
    return TOOL_TEMPLATE_NAME if is_tool else CHAT_TEMPLATE_NAME


def compute_license_info(model_path: str, is_tool: bool, is_hf_model: bool) -> Dict[str, str]:
    """Return license info dict with keys: license, license_name, license_link."""
    if is_tool:
        if "Hammer2.1-1.5b" in model_path:
            return {
                "license": "cc-by-nc-4.0",
                "license_name": "CC BY-NC 4.0",
                "license_link": f"https://huggingface.co/{model_path}/blob/main/LICENSE" if is_hf_model else "",
            }
        return {
            "license": "other",
            "license_name": "qwen-research",
            "license_link": f"https://huggingface.co/{model_path}/blob/main/LICENSE" if is_hf_model else "",
        }

    # Chat models default to Apache 2.0
    return {
        "license": "apache-2.0",
        "license_name": "Apache 2.0",
        "license_link": "",
    }


__all__ = [
    "CHAT_TEMPLATE_NAME",
    "TOOL_TEMPLATE_NAME",
    "resolve_template_name",
    "compute_license_info",
]


