"""Template and license configuration for AWQ README generation."""

from __future__ import annotations



CHAT_TEMPLATE_NAME = "awq_chat_template.md"
TOOL_TEMPLATE_NAME = "awq_tool_template.md"

_MISTRAL_RESEARCH_MODELS = {
    "TheDrummer/Cydonia-Redux-22B-v1.1",
}

_MISTRAL_RESEARCH_LICENSE = {
    "license": "other",
    "license_name": "MRL 0.1",
    "license_link": "https://mistral.ai/licenses/MRL-0.1.md",
}

_QWEN_LICENSE_MODELS = {
    "Sao10K/14B-Qwen2.5-Kunou-v1",
}

_QWEN_LICENSE = {
    "license": "other",
    "license_name": "qwen",
    "license_link": "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/blob/main/LICENSE",
}


def resolve_template_name(is_tool: bool) -> str:
    return TOOL_TEMPLATE_NAME if is_tool else CHAT_TEMPLATE_NAME


def _is_mistral_research_model(model_path: str) -> bool:
    normalized = (model_path or "").strip()
    if not normalized:
        return False
    for target in _MISTRAL_RESEARCH_MODELS:
        if normalized == target or normalized.endswith(target):
            return True
    return False


def _license_link_for(model_path: str, is_hf_model: bool) -> str:
    if not is_hf_model:
        return ""
    return f"https://huggingface.co/{model_path}/blob/main/LICENSE"


def _is_qwen_license_model(model_path: str) -> bool:
    normalized = (model_path or "").strip()
    if not normalized:
        return False
    for target in _QWEN_LICENSE_MODELS:
        if normalized == target or normalized.endswith(target):
            return True
    return False


def compute_license_info(model_path: str, is_tool: bool, is_hf_model: bool) -> dict[str, str]:
    """Return license info dict with keys: license, license_name, license_link."""
    if is_tool:
        if "Hammer2.1-1.5b" in model_path:
            return {
                "license": "cc-by-nc-4.0",
                "license_name": "CC BY-NC 4.0",
                "license_link": _license_link_for(model_path, is_hf_model),
            }
        return {
            "license": "other",
            "license_name": "qwen-research",
            "license_link": _license_link_for(model_path, is_hf_model),
        }

    if _is_mistral_research_model(model_path):
        return _MISTRAL_RESEARCH_LICENSE.copy()

    if _is_qwen_license_model(model_path):
        return _QWEN_LICENSE.copy()

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


