"""Template and license constants for AWQ README generation."""

from __future__ import annotations

CHAT_TEMPLATE_NAME = "awq_chat_template.md"


MISTRAL_RESEARCH_MODELS: frozenset[str] = frozenset({
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B",
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
})

MISTRAL_RESEARCH_LICENSE: dict[str, str] = {
    "license": "other",
    "license_name": "other",
    "license_link": "LICENSE",
}

QWEN_LICENSE_MODELS: frozenset[str] = frozenset({
    "anthracite-org/magnum-v1-32b",
})

QWEN_LICENSE: dict[str, str] = {
    "license": "other",
    "license_name": "other",
    "license_link": "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/blob/main/LICENSE",
}


__all__ = [
    "CHAT_TEMPLATE_NAME",
    "MISTRAL_RESEARCH_MODELS",
    "MISTRAL_RESEARCH_LICENSE",
    "QWEN_LICENSE_MODELS",
    "QWEN_LICENSE",
]
