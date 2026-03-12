"""Environment validation helpers."""

from __future__ import annotations

import logging
from .models import is_tool_model
from src.config.trt import TRT_ENGINE_DIR
from src.config.secrets import TEXT_API_KEY
from .health import parse_health_allowed_cidrs
from src.config.http import HEALTH_ALLOWED_CIDRS
from src.config.websocket import WS_IDLE_TIMEOUT_S
from src.config.tool import TOOL_DECISION_THRESHOLD
from .quantization import classify_prequantized_model
from src.config.gpu import CHAT_GPU_FRAC, TOOL_GPU_FRAC
from src.tokens.validation import validate_model_tokenizer
from src.config.timeouts import CHAT_TIMEOUT_S, TOOL_TIMEOUT_S
from src.config.engine import INFERENCE_ENGINE, CHAT_QUANTIZATION
from src.config.quantization import SUPPORTED_ENGINES, VALID_QUANT_FORMATS
from src.config.deploy import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL
from src.config.sampling import (
    CHAT_MIN_P,
    CHAT_TOP_K,
    CHAT_TOP_P,
    CHAT_TEMPERATURE,
    CHAT_PRESENCE_PENALTY,
    CHAT_FREQUENCY_PENALTY,
    CHAT_REPETITION_PENALTY,
)
from src.config.limits import (
    CHAT_MAX_LEN,
    CHAT_MAX_OUT,
    CHAT_MIN_P_MAX,
    CHAT_MIN_P_MIN,
    CHAT_TOP_K_MAX,
    CHAT_TOP_K_MIN,
    CHAT_TOP_P_MAX,
    CHAT_TOP_P_MIN,
    USER_UTT_MAX_TOKENS,
    CHAT_TEMPERATURE_MAX,
    CHAT_TEMPERATURE_MIN,
    HISTORY_RETENTION_PCT,
    CHAT_PROMPT_MAX_TOKENS,
    TRIMMED_HISTORY_LENGTH,
    CHAT_HISTORY_MAX_TOKENS,
    CHAT_PRESENCE_PENALTY_MAX,
    CHAT_PRESENCE_PENALTY_MIN,
    CHAT_FREQUENCY_PENALTY_MAX,
    CHAT_FREQUENCY_PENALTY_MIN,
    MAX_CONCURRENT_CONNECTIONS,
    CHAT_REPETITION_PENALTY_MAX,
    CHAT_REPETITION_PENALTY_MIN,
)

logger = logging.getLogger(__name__)


def _allow_prequantized_override(model: str | None, model_type: str) -> bool:
    if model_type != "chat":
        return False
    quant = (CHAT_QUANTIZATION or "").lower()
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


def _validate_numeric_bounds() -> list[str]:
    """Check numeric config values are within valid ranges."""
    errors: list[str] = []

    bounds: tuple[tuple[str, float | int, float | int, float | int], ...] = (
        ("HISTORY_RETENTION_PCT", HISTORY_RETENTION_PCT, 30, 90),
        ("CHAT_TEMPERATURE", CHAT_TEMPERATURE, CHAT_TEMPERATURE_MIN, CHAT_TEMPERATURE_MAX),
        ("CHAT_TOP_P", CHAT_TOP_P, CHAT_TOP_P_MIN, CHAT_TOP_P_MAX),
        ("CHAT_TOP_K", CHAT_TOP_K, CHAT_TOP_K_MIN, CHAT_TOP_K_MAX),
        ("CHAT_MIN_P", CHAT_MIN_P, CHAT_MIN_P_MIN, CHAT_MIN_P_MAX),
        ("CHAT_REPETITION_PENALTY", CHAT_REPETITION_PENALTY, CHAT_REPETITION_PENALTY_MIN, CHAT_REPETITION_PENALTY_MAX),
        ("CHAT_PRESENCE_PENALTY", CHAT_PRESENCE_PENALTY, CHAT_PRESENCE_PENALTY_MIN, CHAT_PRESENCE_PENALTY_MAX),
        ("CHAT_FREQUENCY_PENALTY", CHAT_FREQUENCY_PENALTY, CHAT_FREQUENCY_PENALTY_MIN, CHAT_FREQUENCY_PENALTY_MAX),
        ("TOOL_DECISION_THRESHOLD", TOOL_DECISION_THRESHOLD, 0.0, 1.0),
        ("WS_IDLE_TIMEOUT_S", WS_IDLE_TIMEOUT_S, 1.0, 86400.0),
        ("CHAT_TIMEOUT_S", CHAT_TIMEOUT_S, 1.0, 600.0),
        ("TOOL_TIMEOUT_S", TOOL_TIMEOUT_S, 0.1, 120.0),
        ("CHAT_GPU_FRAC", CHAT_GPU_FRAC, 0.01, 1.0),
        ("TOOL_GPU_FRAC", TOOL_GPU_FRAC, 0.01, 1.0),
    )

    for name, value, lo, hi in bounds:
        if not (lo <= value <= hi):
            errors.append(f"{name} must be {lo}-{hi}, got {value}")

    positive_ints: tuple[tuple[str, int], ...] = (
        ("CHAT_PROMPT_MAX_TOKENS", CHAT_PROMPT_MAX_TOKENS),
        ("CHAT_HISTORY_MAX_TOKENS", CHAT_HISTORY_MAX_TOKENS),
        ("USER_UTT_MAX_TOKENS", USER_UTT_MAX_TOKENS),
        ("CHAT_MAX_LEN", CHAT_MAX_LEN),
        ("CHAT_MAX_OUT", CHAT_MAX_OUT),
    )

    for name, value in positive_ints:
        if value <= 0:
            errors.append(f"{name} must be positive, got {value}")

    return errors


def validate_env() -> None:
    """Validate required configuration once during startup."""
    errors: list[str] = []

    # Required secrets
    if not TEXT_API_KEY:
        errors.append("TEXT_API_KEY environment variable is required")

    # Required limits
    if MAX_CONCURRENT_CONNECTIONS is None:
        errors.append("MAX_CONCURRENT_CONNECTIONS environment variable is required")
    elif MAX_CONCURRENT_CONNECTIONS <= 0:
        errors.append("MAX_CONCURRENT_CONNECTIONS must be a positive integer (>= 1)")

    # History trimming configuration
    if TRIMMED_HISTORY_LENGTH >= CHAT_HISTORY_MAX_TOKENS:
        errors.append(
            f"TRIMMED_HISTORY_LENGTH ({TRIMMED_HISTORY_LENGTH}) must be less than "
            f"CHAT_HISTORY_MAX_TOKENS ({CHAT_HISTORY_MAX_TOKENS})"
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
        elif CHAT_QUANTIZATION.lower() not in VALID_QUANT_FORMATS:
            errors.append(
                f"Invalid CHAT_QUANTIZATION='{CHAT_QUANTIZATION}'. "
                f"Valid formats: {', '.join(sorted(VALID_QUANT_FORMATS))}"
            )

    # Validate tokenizers exist locally for configured models
    chat_tok_error = validate_model_tokenizer(CHAT_MODEL, "CHAT_MODEL", DEPLOY_CHAT)
    if chat_tok_error:
        errors.append(chat_tok_error)

    tool_tok_error = validate_model_tokenizer(TOOL_MODEL, "TOOL_MODEL", DEPLOY_TOOL)
    if tool_tok_error:
        errors.append(tool_tok_error)

    errors.extend(_validate_numeric_bounds())

    try:
        parse_health_allowed_cidrs(HEALTH_ALLOWED_CIDRS)
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        raise ValueError("; ".join(errors))


__all__ = [
    "validate_env",
    "_allow_prequantized_override",
]
