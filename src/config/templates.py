"""Template and license configuration for AWQ README generation."""

from __future__ import annotations


CHAT_TEMPLATE_NAME = "awq_chat_template.md"


_MISTRAL_RESEARCH_MODELS = {
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B",
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
}

_MISTRAL_RESEARCH_LICENSE = {
    "license": "other",
    "license_name": "other",
    "license_link": "LICENSE",
}

_QWEN_LICENSE_MODELS = {
    "anthracite-org/magnum-v1-32b",
}

_QWEN_LICENSE = {
    "license": "other",
    "license_name": "other",
    "license_link": "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/blob/main/LICENSE",
}


def resolve_template_name(is_tool: bool) -> str:
    return CHAT_TEMPLATE_NAME


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
        return "LICENSE"
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
        return {
            "license": "other",
            "license_name": "other",
            "license_link": _license_link_for(model_path, is_hf_model),
        }

    if _is_mistral_research_model(model_path):
        license_info = _MISTRAL_RESEARCH_LICENSE.copy()
        if license_info.get("license_link") == "LICENSE" and is_hf_model:
            license_info["license_link"] = _license_link_for(model_path, is_hf_model)
        return license_info

    if _is_qwen_license_model(model_path):
        return _QWEN_LICENSE.copy()

    # Chat models default to Apache 2.0
    return {
        "license": "apache-2.0",
        "license_name": "apache-2.0",
        "license_link": "LICENSE",
    }


__all__ = [
    "CHAT_TEMPLATE_NAME",
    "resolve_template_name",
    "compute_license_info",
]


