"""Environment validation helpers."""

from __future__ import annotations

from src.config.deploy import DEPLOY_CHAT, DEPLOY_TOOL, CHAT_MODEL, TOOL_MODEL
from src.config.engine import INFERENCE_ENGINE, QUANTIZATION, CHAT_QUANTIZATION
from src.config.trt import TRT_ENGINE_DIR
from src.config.quantization import SUPPORTED_ENGINES
from src.config.limits import MAX_CONCURRENT_CONNECTIONS
from src.config.secrets import TEXT_API_KEY
from .models import is_classifier_model
from .quantization import classify_prequantized_model


def _effective_chat_quantization() -> str:
    return (CHAT_QUANTIZATION or QUANTIZATION or "").lower()


def _allow_prequantized_override(model: str | None, model_type: str) -> bool:
    if model_type != "chat":
        return False
    quant = _effective_chat_quantization()
    if not model or not quant:
        return False
    kind = classify_prequantized_model(model)
    if not kind:
        return False
    if quant == "awq" and kind != "awq":
        return False
    if quant.startswith("gptq") and kind != "gptq":
        return False
    if kind not in {"awq", "gptq"}:
        return False
    print(f"[WARNING] Using pre-quantized {kind.upper()} {model_type} model not in approved list: {model}")
    return True


def validate_env() -> None:
    """Validate required configuration once during startup."""
    errors: list[str] = []
    
    # Required secrets
    if not TEXT_API_KEY:
        errors.append("TEXT_API_KEY environment variable is required")
    
    # Required limits
    if MAX_CONCURRENT_CONNECTIONS is None:
        errors.append("MAX_CONCURRENT_CONNECTIONS environment variable is required")
    
    # Model configuration
    if DEPLOY_CHAT and not CHAT_MODEL:
        errors.append("CHAT_MODEL is required when DEPLOY_MODE is 'both' or 'chat'")
    if DEPLOY_TOOL and not TOOL_MODEL:
        errors.append("TOOL_MODEL is required when DEPLOY_MODE is 'both' or 'tool'")
    if DEPLOY_TOOL and TOOL_MODEL and not is_classifier_model(TOOL_MODEL):
        errors.append("TOOL_MODEL must be one of the classifier models (vLLM tool engines are disabled)")
    
    # Validate engine selection
    if INFERENCE_ENGINE not in SUPPORTED_ENGINES:
        errors.append(f"INFERENCE_ENGINE must be one of {SUPPORTED_ENGINES}, got: {INFERENCE_ENGINE}")
    
    # TRT-specific validation
    if INFERENCE_ENGINE == "trt" and DEPLOY_CHAT:
        if not TRT_ENGINE_DIR:
            # TRT_ENGINE_DIR can be empty if we're building from scratch
            pass  # Will be set during quantization/build step
    # Quantization is only required when deploying LLMs (not classifiers)
    needs_quantization = DEPLOY_CHAT or (DEPLOY_TOOL and not is_classifier_model(TOOL_MODEL))
    if needs_quantization:
        if not QUANTIZATION:
            errors.append("QUANTIZATION environment variable is required for LLM models")
        elif INFERENCE_ENGINE == "vllm" and QUANTIZATION not in {"fp8", "gptq", "gptq_marlin", "awq", "8bit", "4bit"}:
            errors.append(
                "QUANTIZATION must be one of 'fp8', 'gptq', 'gptq_marlin', 'awq', '8bit', or '4bit' for VLLM"
            )
        elif INFERENCE_ENGINE == "trt" and QUANTIZATION not in {
            "fp8", "int8_sq", "int8", "int4_awq", "awq", "8bit", "4bit"
        }:
            errors.append(
                "QUANTIZATION must be one of 'fp8', 'int8_sq', 'int8', 'int4_awq', 'awq', '8bit', or '4bit' for TRT"
            )
    if errors:
        raise ValueError("; ".join(errors))


__all__ = [
    "validate_env",
    "_effective_chat_quantization",
    "_allow_prequantized_override",
]
