"""Aggregator of configuration modules.

This module re-exports the config API from smaller modules:
- env: environment initialization and core env values
- models: allowlists and validation helpers
- limits: token and concurrency limits
- secrets: secrets like API_KEY
- engine_args: make_engine_args utility
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
    CHECK_SCREEN_PREFIX,
    SCREEN_CHECKED_PREFIX,
)
from .models import (
    ALLOWED_CHAT_MODELS,
    ALLOWED_TOOL_MODELS,
    _is_awq_model,
    is_valid_model as _is_valid_model,
)
from .limits import (
    CHAT_MAX_LEN,
    CHAT_MAX_OUT,
    TOOL_MAX_OUT,
    TOOL_MAX_LEN,
    CHAT_TEMPERATURE_MIN,
    CHAT_TEMPERATURE_MAX,
    CHAT_TOP_P_MIN,
    CHAT_TOP_P_MAX,
    CHAT_TOP_K_MIN,
    CHAT_TOP_K_MAX,
    CHAT_MIN_P_MIN,
    CHAT_MIN_P_MAX,
    CHAT_REPEAT_PENALTY_MIN,
    CHAT_REPEAT_PENALTY_MAX,
    CHAT_PRESENCE_PENALTY_MIN,
    CHAT_PRESENCE_PENALTY_MAX,
    CHAT_FREQUENCY_PENALTY_MIN,
    CHAT_FREQUENCY_PENALTY_MAX,
    CHAT_PROMPT_MAX_TOKENS,
    TOOL_PROMPT_MAX_TOKENS,
    PERSONALITY_MAX_LEN,
    STREAM_FLUSH_MS,
    HISTORY_MAX_TOKENS,
    USER_UTT_MAX_TOKENS,
    TOOL_HISTORY_TOKENS,
    TOOL_SYSTEM_TOKENS,
    EXACT_TOKEN_TRIM,
    CONCURRENT_MODEL_CALL,
    MAX_CONCURRENT_CONNECTIONS,
)
from .secrets import TEXT_API_KEY
from .args import make_engine_args
from .websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_WATCHDOG_TICK_S,
    WS_HANDSHAKE_ACQUIRE_TIMEOUT_S,
    WS_CLOSE_UNAUTHORIZED_CODE,
    WS_CLOSE_BUSY_CODE,
    WS_CLOSE_IDLE_CODE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)


# Validate models with the same logic as before, raising on invalid
if DEPLOY_CHAT and not _is_valid_model(CHAT_MODEL, ALLOWED_CHAT_MODELS, "chat"):
    if QUANTIZATION == "awq" and _is_awq_model(CHAT_MODEL):
        print(f"[WARNING] Using AWQ model not in approved list: {CHAT_MODEL}")
    else:
        raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")

if DEPLOY_TOOL and not _is_valid_model(TOOL_MODEL, ALLOWED_TOOL_MODELS, "tool"):
    if QUANTIZATION == "awq" and _is_awq_model(TOOL_MODEL):
        print(f"[WARNING] Using AWQ model not in approved list: {TOOL_MODEL}")
    else:
        raise ValueError(f"TOOL_MODEL must be one of: {ALLOWED_TOOL_MODELS}, got: {TOOL_MODEL}")

# Additional safety: AWQ requires non-GPTQ chat weights (except for pre-quantized AWQ models)
if (QUANTIZATION == "awq" and DEPLOY_CHAT and CHAT_MODEL and 
    "GPTQ" in CHAT_MODEL and not _is_awq_model(CHAT_MODEL)):
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
    # prefixes
    "CHECK_SCREEN_PREFIX",
    "SCREEN_CHECKED_PREFIX",
    # models/validation
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    # limits
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "TOOL_MAX_OUT",
    "TOOL_MAX_LEN",
    "CHAT_TEMPERATURE_MIN",
    "CHAT_TEMPERATURE_MAX",
    "CHAT_TOP_P_MIN",
    "CHAT_TOP_P_MAX",
    "CHAT_TOP_K_MIN",
    "CHAT_TOP_K_MAX",
    "CHAT_MIN_P_MIN",
    "CHAT_MIN_P_MAX",
    "CHAT_REPEAT_PENALTY_MIN",
    "CHAT_REPEAT_PENALTY_MAX",
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
    "TOOL_HISTORY_TOKENS",
    "TOOL_SYSTEM_TOKENS",
    "EXACT_TOKEN_TRIM",
    "CONCURRENT_MODEL_CALL",
    "MAX_CONCURRENT_CONNECTIONS",
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
    # helpers
    "make_engine_args",
]
