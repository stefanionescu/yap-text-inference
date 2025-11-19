"""Model allowlists and validation helpers, including AWQ support."""

import os

from .env import QUANTIZATION


ALLOWED_CHAT_MODELS: list[str] = [
    # Full precision models
    "kyx0r/Neona-12B",
    "SicariusSicariiStuff/Impish_Nemo_12B",
    "SicariusSicariiStuff/Impish_Magic_24B",
    "SicariusSicariiStuff/Wingless_Imp_8B",
    "SicariusSicariiStuff/Impish_Mind_8B",
    "SicariusSicariiStuff/Eximius_Persona_5B",
    "SicariusSicariiStuff/Impish_LLAMA_4B",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B",
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",
    "SicariusSicariiStuff/Impish_Magic_24B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B_GPTQ-4-bit-128",
    # Pre-quantized AWQ models
    "yapwithai/impish-12b-awq",
]

ALLOWED_TOOL_MODELS: list[str] = [
    # Full precision models
    "MadeAgents/Hammer2.1-1.5b",
    "MadeAgents/Hammer2.1-3b",
    # Pre-quantized AWQ models
    "yapwithai/hammer-2.1-3b-awq",
]


def _is_local_model_path(value: str | None) -> bool:
    if not value:
        return False
    try:
        return os.path.exists(value)
    except Exception:
        return False


def _is_awq_model(value: str | None) -> bool:
    """Check if model name suggests it's a pre-quantized AWQ model."""
    if not value:
        return False
    return "awq" in value.lower() and "/" in value


def is_valid_model(model: str, allowed_models: list, model_type: str) -> bool:
    """Enhanced model validation with AWQ support."""
    if not model:
        return False

    # Check if it's in the explicit allowed list
    if model in allowed_models:
        return True

    # Check if it's a local path
    if _is_local_model_path(model):
        return True

    # For AWQ quantization, be more permissive with AWQ model names
    if QUANTIZATION == "awq" and _is_awq_model(model):
        return True

    return False


__all__ = [
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "_is_local_model_path",
    "_is_awq_model",
    "is_valid_model",
]


