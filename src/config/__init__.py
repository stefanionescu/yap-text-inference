"""Aggregator of configuration modules.

This module re-exports the config API from smaller modules:
- env: environment initialization and core env values
- models: allowlists and validation helpers
- limits: token and concurrency limits
- secrets: secrets like API_KEY
"""

from .env import (
    configure_runtime_env,
    DEPLOY_MODELS,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CHAT_MODEL,
    TOOL_MODEL,
    CHAT_GPU_FRAC,
    TOOL_GPU_FRAC,
    KV_DTYPE,
    QUANTIZATION,
    CHAT_QUANTIZATION,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
    CHAT_TEMPLATE_ENABLE_THINKING,
    CACHE_RESET_INTERVAL_SECONDS,
    CACHE_RESET_MIN_SESSION_SECONDS,
    TOOL_LANGUAGE_FILTER,
    # Tool classifier settings
    TOOL_DECISION_THRESHOLD,
    TOOL_COMPILE,
    TOOL_HISTORY_TOKENS,
    TOOL_MAX_LENGTH,
    TOOL_MICROBATCH_MAX_SIZE,
    TOOL_MICROBATCH_MAX_DELAY_MS,
)
from .models import (
    ALLOWED_CHAT_MODELS,
    ALLOWED_TOOL_MODELS,
    classify_prequantized_model,
    is_valid_model as _is_valid_model,
    is_classifier_model,
)
from .priorities import (
    CHAT_REQUEST_PRIORITY,
    TOOL_REQUEST_PRIORITY,
    WARM_REQUEST_PRIORITY,
)
from .quantization import is_awq_model_name
from .limits import (
    CHAT_MAX_LEN,
    CHAT_MAX_OUT,
    PROMPT_SANITIZE_MAX_CHARS,
    CHAT_TEMPERATURE_MIN,
    CHAT_TEMPERATURE_MAX,
    CHAT_TOP_P_MIN,
    CHAT_TOP_P_MAX,
    CHAT_TOP_K_MIN,
    CHAT_TOP_K_MAX,
    CHAT_MIN_P_MIN,
    CHAT_MIN_P_MAX,
    CHAT_REPETITION_PENALTY_MIN,
    CHAT_REPETITION_PENALTY_MAX,
    CHAT_PRESENCE_PENALTY_MIN,
    CHAT_PRESENCE_PENALTY_MAX,
    CHAT_FREQUENCY_PENALTY_MIN,
    CHAT_FREQUENCY_PENALTY_MAX,
    CHAT_PROMPT_MAX_TOKENS,
    PERSONALITY_MAX_LEN,
    STREAM_FLUSH_MS,
    HISTORY_MAX_TOKENS,
    USER_UTT_MAX_TOKENS,
    CHAT_PROMPT_UPDATE_WINDOW_SECONDS,
    CHAT_PROMPT_UPDATE_MAX_PER_WINDOW,
    WS_MESSAGE_WINDOW_SECONDS,
    WS_MAX_MESSAGES_PER_WINDOW,
    WS_CANCEL_WINDOW_SECONDS,
    WS_MAX_CANCELS_PER_WINDOW,
    TOOL_HISTORY_TOKENS,
    EXACT_TOKEN_TRIM,
    MAX_CONCURRENT_CONNECTIONS,
    SCREEN_PREFIX_MAX_CHARS,
)
from .secrets import TEXT_API_KEY
from .websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_WATCHDOG_TICK_S,
    WS_HANDSHAKE_ACQUIRE_TIMEOUT_S,
    WS_CLOSE_UNAUTHORIZED_CODE,
    WS_CLOSE_BUSY_CODE,
    WS_CLOSE_IDLE_CODE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)


# Quantization helpers for override warnings
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


if DEPLOY_CHAT and not _is_valid_model(CHAT_MODEL, ALLOWED_CHAT_MODELS, "chat"):
    if not _allow_prequantized_override(CHAT_MODEL, "chat"):
        raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")

if DEPLOY_TOOL:
    # Tool models must be classifiers
    if not is_classifier_model(TOOL_MODEL):
        raise ValueError("TOOL_MODEL must be a classifier model; vLLM tool engines are no longer supported")
    # Only validate against allowlist for HuggingFace models, not local paths
    from .models import _is_local_model_path
    if not _is_local_model_path(TOOL_MODEL) and TOOL_MODEL not in ALLOWED_TOOL_MODELS:
        raise ValueError(
            f"TOOL_MODEL classifier must be one of: {ALLOWED_TOOL_MODELS}, got: {TOOL_MODEL}"
        )

# Additional safety: AWQ requires non-GPTQ chat weights (except for pre-quantized AWQ models)
if (QUANTIZATION == "awq" and DEPLOY_CHAT and CHAT_MODEL and
    "GPTQ" in CHAT_MODEL and not is_awq_model_name(CHAT_MODEL)):
    raise ValueError(
        "For QUANTIZATION=awq, CHAT_MODEL must be a non-GPTQ (float) model. "
        f"Got: {CHAT_MODEL}. Use a pre-quantized AWQ model or a float model instead."
    )

__all__ = [
    "configure_runtime_env",
    # env/core
    "DEPLOY_MODELS",
    "DEPLOY_CHAT",
    "DEPLOY_TOOL",
    "CHAT_MODEL",
    "TOOL_MODEL",
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "QUANTIZATION",
    "CHAT_QUANTIZATION",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "CACHE_RESET_INTERVAL_SECONDS",
    "CACHE_RESET_MIN_SESSION_SECONDS",
    "TOOL_LANGUAGE_FILTER",
    # tool classifier settings
    "TOOL_DECISION_THRESHOLD",
    "TOOL_COMPILE",
    "TOOL_HISTORY_TOKENS",
    "TOOL_MAX_LENGTH",
    "TOOL_MICROBATCH_MAX_SIZE",
    "TOOL_MICROBATCH_MAX_DELAY_MS",
    # prefixes
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
    # models/validation
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "is_classifier_model",
    # limits
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "PROMPT_SANITIZE_MAX_CHARS",
    "CHAT_TEMPERATURE_MIN",
    "CHAT_TEMPERATURE_MAX",
    "CHAT_TOP_P_MIN",
    "CHAT_TOP_P_MAX",
    "CHAT_TOP_K_MIN",
    "CHAT_TOP_K_MAX",
    "CHAT_MIN_P_MIN",
    "CHAT_MIN_P_MAX",
    "CHAT_REPETITION_PENALTY_MIN",
    "CHAT_REPETITION_PENALTY_MAX",
    "CHAT_PRESENCE_PENALTY_MIN",
    "CHAT_PRESENCE_PENALTY_MAX",
    "CHAT_FREQUENCY_PENALTY_MIN",
    "CHAT_FREQUENCY_PENALTY_MAX",
    "CHAT_PROMPT_MAX_TOKENS",
    "PERSONALITY_MAX_LEN",
    "STREAM_FLUSH_MS",
    "HISTORY_MAX_TOKENS",
    "USER_UTT_MAX_TOKENS",
    "CHAT_PROMPT_UPDATE_WINDOW_SECONDS",
    "CHAT_PROMPT_UPDATE_MAX_PER_WINDOW",
    "WS_MESSAGE_WINDOW_SECONDS",
    "WS_MAX_MESSAGES_PER_WINDOW",
    "WS_CANCEL_WINDOW_SECONDS",
    "WS_MAX_CANCELS_PER_WINDOW",
    "TOOL_HISTORY_TOKENS",
    "EXACT_TOKEN_TRIM",
    "MAX_CONCURRENT_CONNECTIONS",
    "SCREEN_PREFIX_MAX_CHARS",
    # secrets
    "TEXT_API_KEY",
    # websocket
    "WS_IDLE_TIMEOUT_S",
    "WS_WATCHDOG_TICK_S",
    "WS_HANDSHAKE_ACQUIRE_TIMEOUT_S",
    "WS_CLOSE_UNAUTHORIZED_CODE",
    "WS_CLOSE_BUSY_CODE",
    "WS_CLOSE_IDLE_CODE",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    # priorities
    "CHAT_REQUEST_PRIORITY",
    "TOOL_REQUEST_PRIORITY",
    "WARM_REQUEST_PRIORITY",
]
