"""Chat prompt routing for supported chat models."""

from __future__ import annotations

import os
from enum import Enum

from .models import ALLOWED_CHAT_MODELS


class ChatPromptFormat(str, Enum):
    """Enumerates the supported chat prompt templates."""

    CHATML = "chatml"
    LLAMA3_INSTRUCT = "llama3_instruct"
    MISTRAL_INSTRUCT = "mistral_instruct"
    GLM = "glm"
    DANCHAT2 = "danchat2"


_LLAMA3_MODELS = {
    "SicariusSicariiStuff/Wingless_Imp_8B",
    "SicariusSicariiStuff/Impish_Mind_8B",
    "SicariusSicariiStuff/Eximius_Persona_5B",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B",
}

_MISTRAL_MODELS = {
    "TheDrummer/Cydonia-Redux-22B-v1.1",
    "TheDrummer/Cydonia-24B-v4.1",
    "TheDrummer/Skyfall-36B-v2",
    "TheDrummer/Magidonia-24B-v4.2.0",
    "dphn/Dolphin-Mistral-24B-Venice-Edition",
    "dphn/dolphin-2.9.3-mistral-nemo-12b",
    "FallenMerick/MN-Violet-Lotus-12B",
    "ReadyArt/Broken-Tutu-24B-Unslop-v2.0",
    "concedo/Beepo-22B",
    "OddTheGreat/Mechanism_24B_V.1",
    "mistralai/Mixtral-8x7B-v0.1",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
}

_GLM_MODELS = {
    "zai-org/glm-4-9b-chat-hf",
    "zai-org/GLM-4-32B-Base-0414",
    "zai-org/GLM-4-32B-0414",
}

_DANCHAT2_MODELS = {
    "PocketDoc/Dans-PersonalityEngine-V1.3.0-24b",
}


def _build_prompt_map() -> dict[str, ChatPromptFormat]:
    prompt_map: dict[str, ChatPromptFormat] = {
        model: ChatPromptFormat.CHATML for model in ALLOWED_CHAT_MODELS
    }
    missing = _LLAMA3_MODELS.difference(prompt_map)
    if missing:
        raise RuntimeError(
            "Chat prompt routing misconfigured; the following llama-3 models are not in "
            f"ALLOWED_CHAT_MODELS: {sorted(missing)}"
        )
    for name in _LLAMA3_MODELS:
        prompt_map[name] = ChatPromptFormat.LLAMA3_INSTRUCT
    missing_mistral = _MISTRAL_MODELS.difference(prompt_map)
    if missing_mistral:
        raise RuntimeError(
            "Chat prompt routing misconfigured; the following mistral models are not in "
            f"ALLOWED_CHAT_MODELS: {sorted(missing_mistral)}"
        )
    for name in _MISTRAL_MODELS:
        prompt_map[name] = ChatPromptFormat.MISTRAL_INSTRUCT
    missing_glm = _GLM_MODELS.difference(prompt_map)
    if missing_glm:
        raise RuntimeError(
            "Chat prompt routing misconfigured; the following GLM models are not in "
            f"ALLOWED_CHAT_MODELS: {sorted(missing_glm)}"
        )
    for name in _GLM_MODELS:
        prompt_map[name] = ChatPromptFormat.GLM
    missing_danchat2 = _DANCHAT2_MODELS.difference(prompt_map)
    if missing_danchat2:
        raise RuntimeError(
            "Chat prompt routing misconfigured; the following DanChat-2 models are not in "
            f"ALLOWED_CHAT_MODELS: {sorted(missing_danchat2)}"
        )
    for name in _DANCHAT2_MODELS:
        prompt_map[name] = ChatPromptFormat.DANCHAT2
    return prompt_map


MODEL_PROMPT_FORMAT: dict[str, ChatPromptFormat] = _build_prompt_map()


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def _lookup_model_identifier(model_name: str | None) -> tuple[str | None, ChatPromptFormat | None]:
    for candidate in (_normalize(model_name), _normalize(os.getenv("CHAT_MODEL_NAME"))):
        if not candidate:
            continue
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


