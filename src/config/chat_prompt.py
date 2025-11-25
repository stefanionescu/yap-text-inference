"""Chat prompt routing for supported chat models."""

from __future__ import annotations

import os
from enum import Enum

from .models import ALLOWED_CHAT_MODELS


class ChatPromptFormat(str, Enum):
    """Enumerates the supported chat prompt templates."""

    CHATML = "chatml"
    MISTRAL_INSTRUCT = "mistral_instruct"
    GEMMA = "gemma" # Gemma 1 & 2
    GEMMA3 = "gemma3" # Gemma 3
    KIMI = "kimi"  # Kimi / Kimi Linear (uses <|im_user|>, <|im_assistant|>, <|im_end|>)


_MISTRAL_MODELS: set[str] = {
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B",
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
}

# Gemma 1 & 2 models use <start_of_turn>user/model format
_GEMMA_MODELS: set[str] = {
    "TheDrummer/Big-Tiger-Gemma-27B-v1",
    "TheDrummer/Tiger-Gemma-12B-v3",
}

# Gemma 3 models use <|start_header_id|> format
_GEMMA3_MODELS: set[str] = {
    "leon-se/gemma-3-27b-it-qat-W4A16-G128",
}

# Kimi / Kimi Linear models use <|im_user|>, <|im_assistant|>, <|im_end|> (NOT standard ChatML)
_KIMI_MODELS: set[str] = {
    "cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit",
}

def _build_prompt_map() -> dict[str, ChatPromptFormat]:
    prompt_map: dict[str, ChatPromptFormat] = {
        model: ChatPromptFormat.CHATML for model in ALLOWED_CHAT_MODELS
    }

    # Validate all custom model sets exist in ALLOWED_CHAT_MODELS
    custom_models = {
        "mistral": _MISTRAL_MODELS,
        "gemma": _GEMMA_MODELS,
        "gemma3": _GEMMA3_MODELS,
        "kimi": _KIMI_MODELS,
    }
    for name, model_set in custom_models.items():
        missing = model_set.difference(prompt_map)
        if missing:
            raise RuntimeError(
                f"Chat prompt routing misconfigured; the following {name} models are not in "
                f"ALLOWED_CHAT_MODELS: {sorted(missing)}"
            )

    # Apply format overrides
    for name in _MISTRAL_MODELS:
        prompt_map[name] = ChatPromptFormat.MISTRAL_INSTRUCT
    for name in _GEMMA_MODELS:
        prompt_map[name] = ChatPromptFormat.GEMMA
    for name in _GEMMA3_MODELS:
        prompt_map[name] = ChatPromptFormat.GEMMA3
    for name in _KIMI_MODELS:
        prompt_map[name] = ChatPromptFormat.KIMI

    return prompt_map


MODEL_PROMPT_FORMAT: dict[str, ChatPromptFormat] = _build_prompt_map()


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def _strip_suffix_insensitive(value: str, suffix: str) -> str | None:
    lowered = value.lower()
    if lowered.endswith(suffix):
        return value[: len(value) - len(suffix)]
    return None


def _strip_marker_insensitive(value: str, marker: str) -> str | None:
    lowered = value.lower()
    idx = lowered.find(marker)
    if idx != -1:
        return value[:idx]
    return None


def _generate_aliases(value: str | None) -> list[str]:
    normalized = _normalize(value)
    if not normalized:
        return []
    aliases: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str | None) -> None:
        candidate = (candidate or "").strip()
        if candidate and candidate not in seen:
            aliases.append(candidate)
            seen.add(candidate)

    _add(normalized)
    _add(_strip_suffix_insensitive(normalized, "-awq"))
    _add(_strip_suffix_insensitive(normalized, "_awq"))
    _add(_strip_marker_insensitive(normalized, "_gptq"))
    _add(_strip_marker_insensitive(normalized, "-gptq"))
    return aliases


def _lookup_model_identifier(model_name: str | None) -> tuple[str | None, ChatPromptFormat | None]:
    candidates = []
    candidates.extend(_generate_aliases(model_name))
    candidates.extend(_generate_aliases(os.getenv("CHAT_MODEL_NAME")))
    for candidate in candidates:
        fmt = MODEL_PROMPT_FORMAT.get(candidate)
        if fmt:
            return candidate, fmt
    return None, None


def get_prompt_format_for_model(model_name: str | None) -> ChatPromptFormat:
    """Return the prompt format for the provided model or raise if unmapped."""
    identifier, fmt = _lookup_model_identifier(model_name)
    if fmt:
        return fmt
    pretty_name = identifier or _normalize(model_name) or os.getenv("CHAT_MODEL_NAME") or ""
    raise ValueError(
        "No chat prompt template registered for the selected chat model. "
        f"Set CHAT_MODEL/CHAT_MODEL_NAME to one of {sorted(MODEL_PROMPT_FORMAT)}; "
        f"got '{pretty_name or '<unset>'}'."
    )


def ensure_prompt_format_available(model_name: str | None) -> None:
    """Validate that a prompt mapping exists for the selected chat model."""
    # Propagate the ValueError message if lookup fails.
    get_prompt_format_for_model(model_name)


__all__ = [
    "ChatPromptFormat",
    "MODEL_PROMPT_FORMAT",
    "ensure_prompt_format_available",
    "get_prompt_format_for_model",
]


