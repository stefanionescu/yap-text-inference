"""Model allowlists and validation helpers, including AWQ support."""

import os

from .quantization import (
    classify_prequantized_model,
    is_awq_model_name,
    is_prequantized_model,
)

ALLOWED_CHAT_MODELS: list[str] = [
    # Full precision models
    "SicariusSicariiStuff/Impish_Nemo_12B", # unstable above 0.8 temp; decent <=0.6
    "TheDrummer/Theia-21B-v2", # mid intelligence; ok for cheaper long runs

    "TheDrummer/Rocinante-12B-v1.1", # mid intelligence; downgrade option, weak instructions
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B", # pretty bad overall
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
    "anthracite-org/magnum-v2-32b", # a bit cheesy and yaps too much (good for general RP tho)
    "djuna/magnum-v2-32b-chatml", # yaps too much but might fix with prompting (good for general RP tho)
    "zerofata/MS3.2-PaintedFantasy-Visage-33B", # better than Cydonia but still quirky
    "anthracite-org/magnum-v4-72b", # amazing on OpenRouter but too big
    "anthracite-org/magnum-v1-72b", # amazing on OpenRouter but too big
    "TheDrummer/Big-Tiger-Gemma-27B-v1", # might or might not work depending on vllm setup/version
    "TheDrummer/Tiger-Gemma-12B-v3", # might or might not work depending on vllm setup/version

    "dphn/Dolphin3.0-Llama3.1-8B",
    "ArliAI/DS-R1-Qwen3-8B-ArliAI-RpR-v4-Small",
    "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "nvidia/Llama-3_1-Nemotron-51B-Instruct",
    "mistralai/Ministral-8B-Instruct-2410",
    "zerofata/L3.3-GeneticLemonade-Unleashed-v3-70B",
    "chargoddard/storytime-13b",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "baidu/ERNIE-4.5-21B-A3B-PT",
    "moonshotai/Moonlight-16B-A3B-Instruct",
    "kakaocorp/kanana-1.5-15.7b-a3b-instruct",
    
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",

    # Pre-quantized AWQ/W4A16 models
    "leon-se/gemma-3-27b-it-qat-W4A16-G128",
    "cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit",
    "NaomiBTW/Cydonia-v1.3-Magnum-v4-22B-AWQ", # stupid and random as fuck

    "TheBloke/30B-Lazarus-AWQ", # completely ignores instructions, super dumb
    "cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit", # BEST MODEL FOR NOW
    "warshanks/Ministral-8B-Instruct-2410-AWQ",
    "jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym",

    "yapwithai/zerofata-MS3.2-paintedfantasy-visage-33B-w4a16", # really bad, rambles even with conservative params
    "yapwithai/sicariussicariistuff-impish-nemo-12B-w4a16",
    "yapwithai/thedrummer-theia-21B-v2-w4a16",
    "yapwithai/doctor-shotgun-ms3.2-24B-magnum-diamond-w4a16",
    "yapwithai/thedrummer-rocinante-12B-v1.1-w4a16",
    "yapwithai/knifeayumu-cydonia-v1.3-magnum-v4-22B-w4a16", # stupid, output is a bit messed up, ignores instructions
]

ALLOWED_TOOL_MODELS: list[str] = [
    # Full precision models
    "MadeAgents/Hammer2.1-1.5b",
    "MadeAgents/Hammer2.1-3b",

    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-14B-Instruct",

    # Pre-quantized GPTQ models
    "Qwen/Qwen2.5-1.5B-Instruct-GPTQ-Int4",

    # Pre-quantized AWQ models
    "Qwen/Qwen2-1.5B-Instruct-AWQ",
    "Qwen/Qwen2.5-14B-Instruct-AWQ",
    "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "Qwen/Qwen3-4B-AWQ",
]


def _is_local_model_path(value: str | None) -> bool:
    if not value:
        return False
    try:
        return os.path.exists(value)
    except Exception:
        return False


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

    if is_prequantized_model(model):
        return True

    return False


__all__ = [
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "_is_local_model_path",
    "is_valid_model",
    "classify_prequantized_model",
    "is_prequantized_model",
    "is_awq_model_name",
]


