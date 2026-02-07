"""Model detection and validation helpers."""

from __future__ import annotations

import os
import re

from .quantization import is_prequantized_model


def _get_model_lists():
    """Lazy import model lists to avoid circular imports."""
    from src.config.models import (  # noqa: PLC0415
        ALLOWED_BASE_CHAT_MODELS,
        ALLOWED_BASE_MOE_CHAT_MODELS,
        ALLOWED_TOOL_MODELS,
        ALLOWED_TRT_QUANT_CHAT_MODELS,
        ALLOWED_VLLM_QUANT_CHAT_MODELS,
    )

    return {
        "ALLOWED_BASE_CHAT_MODELS": ALLOWED_BASE_CHAT_MODELS,
        "ALLOWED_BASE_MOE_CHAT_MODELS": ALLOWED_BASE_MOE_CHAT_MODELS,
        "ALLOWED_TOOL_MODELS": ALLOWED_TOOL_MODELS,
        "ALLOWED_VLLM_QUANT_CHAT_MODELS": ALLOWED_VLLM_QUANT_CHAT_MODELS,
        "ALLOWED_TRT_QUANT_CHAT_MODELS": ALLOWED_TRT_QUANT_CHAT_MODELS,
    }


def is_local_model_path(value: str | None) -> bool:
    """Check if value is a local filesystem path to a model."""
    if not value:
        return False
    try:
        return os.path.exists(value)
    except Exception:
        return False


def is_classifier_model(model: str | None) -> bool:
    """Check if model is a classifier (not autoregressive LLM).

    Classifier models use transformers AutoModelForSequenceClassification,
    not vLLM, and cannot be quantized.
    """
    if not model:
        return False
    # Lazy import to avoid circular import
    lists = _get_model_lists()
    # Check explicit allowlist
    if model in lists["ALLOWED_TOOL_MODELS"]:
        return True
    # Accept local paths as classifier models (typically /app/models/tool in Docker)
    # This allows preloaded models to be used without being in the explicit allowlist
    return bool(is_local_model_path(model))


def is_valid_model(model: str, allowed_models: list, model_type: str) -> bool:
    """Enhanced model validation with AWQ support."""
    if not model:
        return False

    # Check if it's in the explicit allowed list
    if model in allowed_models:
        return True

    # Check if it's a local path
    if is_local_model_path(model):
        return True

    return bool(is_prequantized_model(model))


# ============================================================================
# MoE Model Detection
# ============================================================================


def is_moe_model(model: str | None) -> bool:
    """Check if model is a Mixture of Experts (MoE) model.

    MoE models require special handling for quantization:
    - VLLM: AWQ/llmcompressor doesn't support MoE, use pre-quantized models
    - TRT: Use quantize_mixed_precision_moe.py instead of quantize.py
    """
    if not model:
        return False

    # Lazy import to avoid circular import
    lists = _get_model_lists()

    # Check explicit MoE allowlist first
    if model in lists["ALLOWED_BASE_MOE_CHAT_MODELS"]:
        return True

    # Heuristic detection from model identifier
    lowered = model.lower()

    # Qwen3 MoE naming convention: "-aXb" suffix (e.g., qwen3-30b-a3b means 30B total, 3B active)
    if re.search(r"-a\d+b", lowered):
        return True

    # Common MoE markers
    moe_markers = ("moe", "mixtral", "deepseek-v2", "deepseek-v3", "ernie-4.5")
    return any(marker in lowered for marker in moe_markers)


def get_all_base_chat_models() -> list[str]:
    """Return combined list of all base chat models (dense + MoE)."""
    lists = _get_model_lists()
    return lists["ALLOWED_BASE_CHAT_MODELS"] + lists["ALLOWED_BASE_MOE_CHAT_MODELS"]


def get_allowed_chat_models(engine: str = "vllm") -> list[str]:
    """Return allowed chat models for a specific engine.

    For both engines, base models (dense + MoE) can be quantized on-the-fly.
    Additionally, each engine has its own pre-quantized model list.
    """
    lists = _get_model_lists()
    base_models = lists["ALLOWED_BASE_CHAT_MODELS"] + lists["ALLOWED_BASE_MOE_CHAT_MODELS"]
    if engine == "trt":
        return base_models + lists["ALLOWED_TRT_QUANT_CHAT_MODELS"]
    # Default to VLLM
    return base_models + lists["ALLOWED_VLLM_QUANT_CHAT_MODELS"]


__all__ = [
    "is_local_model_path",
    "is_classifier_model",
    "is_valid_model",
    "is_moe_model",
    "get_all_base_chat_models",
    "get_allowed_chat_models",
]
