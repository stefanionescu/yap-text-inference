"""Model allowlists and validation helpers, including AWQ support."""

import os

from .env import QUANTIZATION


ALLOWED_CHAT_MODELS: list[str] = [
    # Full precision models
    "SicariusSicariiStuff/Impish_Nemo_12B", # unstable once it gets past 0.8 temp, not like the model card describes it
    "TheDrummer/Skyfall-36B-v2", # yaps too much and is kinda dumb
    "TheDrummer/Theia-21B-v2", # mid intelligence, not really worth it
    "allura-org/Qwen2.5-32b-RP-Ink", # yaps way too much and hallucinates

    "TheDrummer/Rocinante-12B-v1.1",
    "sam-paech/gemma-3-27b-it-antislop",
    "moonshotai/Kimi-Linear-48B-A3B-Instruct",
    "cerebras/Kimi-Linear-REAP-35B-A3B-Instruct",
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B", # 3
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
    "anthracite-org/magnum-v1-32b",
    "anthracite-org/magnum-v2-32b",
    "djuna/magnum-v2-32b-chatml", # 1
    "intervitens/mini-magnum-12b-v1.1",
    "anthracite-org/magnum-v4-72b",
    "anthracite-org/magnum-v4-12b",

    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",

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


