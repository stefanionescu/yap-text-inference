"""Aggregator of configuration modules.

This module re-exports the config API from smaller modules:
- env: environment initialization and core env values
- models: allowlists and validation helpers
- limits: token and concurrency limits
- secrets: secrets like API_KEY
"""

from .env import (
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
    TOOL_QUANTIZATION,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
    CHAT_TEMPLATE_ENABLE_THINKING,
    CACHE_RESET_INTERVAL_SECONDS,
    CACHE_RESET_MIN_SESSION_SECONDS,
)
from .models import (
    ALLOWED_CHAT_MODELS,
    ALLOWED_TOOL_MODELS,
    classify_prequantized_model,
    is_valid_model as _is_valid_model,
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
    TOOL_MAX_OUT,
    TOOL_MAX_LEN,
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
    TOOL_PROMPT_MAX_TOKENS,
    EXACT_TOKEN_TRIM,
    CONCURRENT_MODEL_CALL,
    MAX_CONCURRENT_CONNECTIONS,
    SCREEN_PREFIX_MAX_CHARS,
    SAFE_LEXER_NAMES,
    CODE_LEXER_KEYWORDS,
    CODE_FENCES,
    CODE_DETECTION_MIN_LENGTH,
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
def _effective_quantization(model_type: str) -> str | None:
    if model_type == "chat":
        return (CHAT_QUANTIZATION or QUANTIZATION or "").lower()
    tool_quant = (TOOL_QUANTIZATION or "").lower()
    if tool_quant:
        return tool_quant
    return (QUANTIZATION or "").lower()


def _allow_prequantized_override(model: str | None, model_type: str) -> bool:
    quant = _effective_quantization(model_type)
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


# Validate models with the same logic as before, raising on invalid
if DEPLOY_CHAT and not _is_valid_model(CHAT_MODEL, ALLOWED_CHAT_MODELS, "chat"):
    if not _allow_prequantized_override(CHAT_MODEL, "chat"):
        raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")

if DEPLOY_TOOL and not _is_valid_model(TOOL_MODEL, ALLOWED_TOOL_MODELS, "tool"):
    if not _allow_prequantized_override(TOOL_MODEL, "tool"):
        raise ValueError(f"TOOL_MODEL must be one of: {ALLOWED_TOOL_MODELS}, got: {TOOL_MODEL}")

# Additional safety: AWQ requires non-GPTQ chat weights (except for pre-quantized AWQ models)
if (QUANTIZATION == "awq" and DEPLOY_CHAT and CHAT_MODEL and
    "GPTQ" in CHAT_MODEL and not is_awq_model_name(CHAT_MODEL)):
    raise ValueError(
        "For QUANTIZATION=awq, CHAT_MODEL must be a non-GPTQ (float) model. "
        f"Got: {CHAT_MODEL}. Use a pre-quantized AWQ model or a float model instead."
    )

__all__ = [
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
    "TOOL_QUANTIZATION",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "CACHE_RESET_INTERVAL_SECONDS",
    "CACHE_RESET_MIN_SESSION_SECONDS",
    # prefixes
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
    # models/validation
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    # limits
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "TOOL_MAX_OUT",
    "TOOL_MAX_LEN",
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
    "TOOL_PROMPT_MAX_TOKENS",
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
    "CONCURRENT_MODEL_CALL",
    "MAX_CONCURRENT_CONNECTIONS",
    "SCREEN_PREFIX_MAX_CHARS",
    "SAFE_LEXER_NAMES",
    "CODE_LEXER_KEYWORDS",
    "CODE_FENCES",
    "CODE_DETECTION_MIN_LENGTH",
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
