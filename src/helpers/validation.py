"""Environment validation helpers."""

from __future__ import annotations

import logging

from src.config.trt import TRT_ENGINE_DIR
from src.config.secrets import TEXT_API_KEY
from src.config.quantization import SUPPORTED_ENGINES
from src.tokens.validation import validate_model_tokenizer
from src.config.engine import INFERENCE_ENGINE, CHAT_QUANTIZATION
from src.config.deploy import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL
from src.config.limits import HISTORY_MAX_TOKENS, TRIMMED_HISTORY_LENGTH, MAX_CONCURRENT_CONNECTIONS

from .models import is_tool_model
from .quantization import classify_prequantized_model

logger = logging.getLogger(__name__)


def _effective_chat_quantization() -> str:
    """Return the effective chat quantization mode."""
    return (CHAT_QUANTIZATION or "").lower()


def _allow_prequantized_override(model: str | None, model_type: str) -> bool:
    if model_type != "chat":
        return False
    quant = _effective_chat_quantization()
    kind = classify_prequantized_model(model) if model else None
    if not model or not quant or not kind:
        return False
    if quant == "awq" and kind != "awq":
        return False
    if quant.startswith("gptq") and kind != "gptq":
        return False
    if kind not in {"awq", "gptq"}:
        return False
    logger.warning(
        "Using pre-quantized %s %s model not in approved list: %s",
        kind.upper(),
        model_type,
        model,
    )
    return True


# Valid quantization formats (internal use - users just need pre-quantized models)
_VALID_QUANT_FORMATS = {"awq", "gptq", "gptq_marlin", "fp8", "int8", "int8_sq", "int4_awq"}


def validate_env() -> None:
    """Validate required configuration once during startup."""
    errors: list[str] = []

    # Required secrets
    if not TEXT_API_KEY:
        errors.append("TEXT_API_KEY environment variable is required")

    # Required limits
    if MAX_CONCURRENT_CONNECTIONS is None:
        errors.append("MAX_CONCURRENT_CONNECTIONS environment variable is required")

    # History trimming configuration
    if TRIMMED_HISTORY_LENGTH >= HISTORY_MAX_TOKENS:
        errors.append(
            f"TRIMMED_HISTORY_LENGTH ({TRIMMED_HISTORY_LENGTH}) must be less than "
            f"HISTORY_MAX_TOKENS ({HISTORY_MAX_TOKENS})"
        )

    # Model configuration
    if DEPLOY_CHAT and not CHAT_MODEL:
        errors.append("CHAT_MODEL is required when DEPLOY_MODE is 'both' or 'chat'")
    if DEPLOY_TOOL and not TOOL_MODEL:
        errors.append("TOOL_MODEL is required when DEPLOY_MODE is 'both' or 'tool'")
    if DEPLOY_TOOL and TOOL_MODEL and not is_tool_model(TOOL_MODEL):
        errors.append("TOOL_MODEL must be one of the tool models (vLLM tool engines are disabled)")

    # Validate engine selection (only relevant when deploying a chat model)
    if DEPLOY_CHAT and INFERENCE_ENGINE not in SUPPORTED_ENGINES:
        errors.append(f"INFERENCE_ENGINE must be one of {SUPPORTED_ENGINES}, got: {INFERENCE_ENGINE}")

    # TRT-specific validation
    if INFERENCE_ENGINE == "trt" and DEPLOY_CHAT and not TRT_ENGINE_DIR:
        # TRT_ENGINE_DIR can be empty if we're building from scratch
        pass  # Will be set during quantization/build step

    # Quantization is required for chat models (auto-detected from name or config files)
    if DEPLOY_CHAT:
        if not CHAT_QUANTIZATION:
            errors.append(
                f"Could not detect quantization from CHAT_MODEL='{CHAT_MODEL}'. "
                "Ensure the model directory contains a config.json with quantization_config.quant_method, "
                "or set CHAT_QUANTIZATION manually."
            )
        elif CHAT_QUANTIZATION.lower() not in _VALID_QUANT_FORMATS:
            errors.append(
                f"Invalid CHAT_QUANTIZATION='{CHAT_QUANTIZATION}'. "
                f"Valid formats: {', '.join(sorted(_VALID_QUANT_FORMATS))}"
            )

    # Validate tokenizers exist locally for configured models
    chat_tok_error = validate_model_tokenizer(CHAT_MODEL, "CHAT_MODEL", DEPLOY_CHAT)
    if chat_tok_error:
        errors.append(chat_tok_error)

    tool_tok_error = validate_model_tokenizer(TOOL_MODEL, "TOOL_MODEL", DEPLOY_TOOL)
    if tool_tok_error:
        errors.append(tool_tok_error)

    if errors:
        raise ValueError("; ".join(errors))


__all__ = [
    "validate_env",
    "_effective_chat_quantization",
    "_allow_prequantized_override",
]
