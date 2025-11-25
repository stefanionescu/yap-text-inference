"""Model allowlists and validation helpers, including AWQ support."""

import os

from .quantization import (
    classify_prequantized_model,
    is_awq_model_name,
    is_prequantized_model,
)


_BLOCKED_MODEL_KEYWORDS = ("gemma", "kimi")

ALLOWED_CHAT_MODELS: list[str] = [
    # Full precision models
    "SicariusSicariiStuff/Impish_Nemo_12B", # 1 unstable once it gets past 0.8 temp, not like the model card describes it; sorta decent at temp <=0.6
    "TheDrummer/Theia-21B-v2", # mid intelligence, overall meh but good if you start to be poor and need to keep running inference

    "TheDrummer/Rocinante-12B-v1.1", # mid intelligence, good if you need to downgrade quality temporarily
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B", # good, need further tests
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
    "anthracite-org/magnum-v2-32b", # a bit cheesy and yaps too much (good for general RP tho)
    "djuna/magnum-v2-32b-chatml", # yaps too much but might fix with prompting (good for general RP tho)
    "anthracite-org/magnum-v4-72b", # amazing on OpenRouter but too big on L40S even after 4bit quant
    "zerofata/MS3.2-PaintedFantasy-Visage-33B", # 3
    
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",

    # Pre-quantized AWQ/W4A16 models
    "leon-se/gemma-3-27b-it-qat-W4A16-G128",
    "cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit",
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
def _is_blocked_model_name(value: str | None) -> bool:
    """Block Gemma/Kimi repos unless they are explicitly pre-quantized."""
    if not value:
        return False
    lower_value = value.lower()
    if not any(keyword in lower_value for keyword in _BLOCKED_MODEL_KEYWORDS):
        return False
    return not is_prequantized_model(value)


def is_valid_model(model: str, allowed_models: list, model_type: str) -> bool:
    """Enhanced model validation with AWQ support."""
    if not model:
        return False

    if _is_blocked_model_name(model):
        return False

    # Check if it's in the explicit allowed list
    if model in allowed_models:
        return True

    # Check if it's a local path
    if _is_local_model_path(model):
        return True

    if is_prequantized_model(model):
        return True

    return False


__all__ = [
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "_is_local_model_path",
    "_is_blocked_model_name",
    "is_valid_model",
    "classify_prequantized_model",
    "is_prequantized_model",
    "is_awq_model_name",
]


