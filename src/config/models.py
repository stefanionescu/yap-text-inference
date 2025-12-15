"""Model allowlists and validation helpers, including quantization support."""

import os
import re

from .quantization import (
    classify_prequantized_model,
    classify_trt_prequantized_model,
    is_awq_model_name,
    is_prequantized_model,
    is_trt_prequantized_model,
)

ALLOWED_BASE_CHAT_MODELS: list[str] = [
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
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "nvidia/Llama-3_1-Nemotron-51B-Instruct",
    "mistralai/Ministral-8B-Instruct-2410",
    "zerofata/L3.3-GeneticLemonade-Unleashed-v3-70B",
    "chargoddard/storytime-13b",
    "Qwen/Qwen3-14B",
    "soob3123/GrayLine-Qwen3-14B",
    "Jinx-org/Jinx-Qwen3-32B",
    "Jinx-org/Jinx-Qwen3-14B",
    "deepseek-ai/DeepSeek-V2-Lite-Chat",
    "mistralai/Mistral-Nemo-Instruct-2407",
    "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "TheDrummer/UnslopNemo-12B-v4.1", # PRETTY GOOD: needs more testing tho
]

ALLOWED_BASE_MOE_CHAT_MODELS: list[str] = [
    "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "ArliAI/Qwen3-30B-A3B-ArliAI-RpR-v4-Fast",
    "DavidAU/Qwen3-33B-A3B-Stranger-Thoughts-IPONDER",
    "Ewere/Qwen3-30B-A3B-abliterated-erotic",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "baidu/ERNIE-4.5-21B-A3B-PT",
    "moonshotai/Moonlight-16B-A3B-Instruct",
    "kakaocorp/kanana-1.5-15.7b-a3b-instruct",
]

ALLOWED_VLLM_QUANT_CHAT_MODELS: list[str] = [
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",

    # Pre-quantized AWQ/W4A16 models
    "leon-se/gemma-3-27b-it-qat-W4A16-G128",
    "cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit",
    "NaomiBTW/Cydonia-v1.3-Magnum-v4-22B-AWQ", # stupid and random as fuck
    "TheBloke/30B-Lazarus-AWQ", # completely ignores instructions, super dumb
    "cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit", # BEST CHAT MODEL FOR NOW
    "Qwen/Qwen3-32B-AWQ",
    "Qwen/Qwen3-14B-AWQ",
    "warshanks/Ministral-8B-Instruct-2410-AWQ",
    "TheBloke/mixtral-8x7b-v0.1-AWQ",
    "casperhansen/mistral-nemo-instruct-2407-awq",
    "cpatonn/Llama-3_3-Nemotron-Super-49B-v1_5-AWQ-4bit",
    "jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym", # EXTREMELY GOOD: might even be better than Qwen3 30B
    "yapwithai/zerofata-MS3.2-paintedfantasy-visage-33B-w4a16", # really bad, rambles even with conservative params
    "yapwithai/sicariussicariistuff-impish-nemo-12B-w4a16",
    "yapwithai/thedrummer-theia-21B-v2-w4a16",
    "yapwithai/doctor-shotgun-ms3.2-24B-magnum-diamond-w4a16",
    "yapwithai/thedrummer-rocinante-12B-v1.1-w4a16",
    "yapwithai/knifeayumu-cydonia-v1.3-magnum-v4-22B-w4a16", # stupid, output is a bit messed up, ignores instructions
]

ALLOWED_TRT_QUANT_CHAT_MODELS: list[str] = []

ALLOWED_TOOL_MODELS: list[str] = [
    "yapwithai/yap-longformer-screenshot-intent",
    "yapwithai/yap-modernbert-screenshot-intent"
]


def is_classifier_model(model: str | None) -> bool:
    """Check if model is a classifier (not autoregressive LLM).
    
    Classifier models use transformers AutoModelForSequenceClassification,
    not vLLM, and cannot be quantized.
    """
    if not model:
        return False
    # Check explicit allowlist
    if model in ALLOWED_TOOL_MODELS:
        return True
    # Accept local paths as classifier models (typically /app/models/tool in Docker)
    # This allows preloaded models to be used without being in the explicit allowlist
    if _is_local_model_path(model):
        return True
    return False


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


# ----------------- MoE Model Detection -----------------

def is_moe_model(model: str | None) -> bool:
    """Check if model is a Mixture of Experts (MoE) model.
    
    MoE models require special handling for quantization:
    - VLLM: AWQ/llmcompressor doesn't support MoE, use pre-quantized models
    - TRT: Use quantize_mixed_precision_moe.py instead of quantize.py
    """
    if not model:
        return False
    
    # Check explicit MoE allowlist first
    if model in ALLOWED_BASE_MOE_CHAT_MODELS:
        return True
    
    # Heuristic detection from model identifier
    lowered = model.lower()
    
    # Qwen3 MoE naming convention: "-aXb" suffix (e.g., qwen3-30b-a3b means 30B total, 3B active)
    if re.search(r"-a\d+b", lowered):
        return True
    
    # Common MoE markers
    moe_markers = ("moe", "mixtral", "deepseek-v2", "deepseek-v3", "ernie-4.5")
    if any(marker in lowered for marker in moe_markers):
        return True
    
    return False


def get_all_base_chat_models() -> list[str]:
    """Return combined list of all base chat models (dense + MoE)."""
    return ALLOWED_BASE_CHAT_MODELS + ALLOWED_BASE_MOE_CHAT_MODELS


def get_allowed_chat_models(engine: str = "vllm") -> list[str]:
    """Return allowed chat models for a specific engine.
    
    For both engines, base models (dense + MoE) can be quantized on-the-fly.
    Additionally, each engine has its own pre-quantized model list.
    """
    base_models = get_all_base_chat_models()
    if engine == "trt":
        return base_models + ALLOWED_TRT_QUANT_CHAT_MODELS
    # Default to VLLM
    return base_models + ALLOWED_VLLM_QUANT_CHAT_MODELS


# Convenience alias for backward compatibility
ALLOWED_CHAT_MODELS = ALLOWED_BASE_CHAT_MODELS + ALLOWED_BASE_MOE_CHAT_MODELS + ALLOWED_VLLM_QUANT_CHAT_MODELS


__all__ = [
    # Model lists
    "ALLOWED_BASE_CHAT_MODELS",
    "ALLOWED_BASE_MOE_CHAT_MODELS",
    "ALLOWED_VLLM_QUANT_CHAT_MODELS",
    "ALLOWED_TRT_QUANT_CHAT_MODELS",
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    # Validation helpers
    "_is_local_model_path",
    "is_valid_model",
    "is_classifier_model",
    # MoE detection
    "is_moe_model",
    "get_all_base_chat_models",
    "get_allowed_chat_models",
    # Quantization detection (re-exported)
    "classify_prequantized_model",
    "classify_trt_prequantized_model",
    "is_prequantized_model",
    "is_trt_prequantized_model",
    "is_awq_model_name",
]
