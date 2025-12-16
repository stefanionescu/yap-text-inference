"""Aggregator of configuration modules.

This module re-exports the config API from smaller modules:
- deploy: deployment mode and model selection
- gpu: GPU memory and architecture
- engine: inference engine selection
- trt: TensorRT-LLM specific settings
- chat: chat behavior settings
- tool: tool classifier settings
- models: allowlists
- limits: token and concurrency limits
- secrets: secrets like API_KEY

Functions have been moved to src/helpers/.
"""

from .deploy import (
    DEPLOY_MODELS,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CHAT_MODEL,
    TOOL_MODEL,
)
from .gpu import (
    CHAT_GPU_FRAC,
    TOOL_GPU_FRAC,
    KV_DTYPE,
    GPU_SM_ARCH,
)
from .engine import (
    INFERENCE_ENGINE,
    QUANTIZATION,
    CHAT_QUANTIZATION,
)
from .trt import (
    TRT_ENGINE_DIR,
    TRT_CHECKPOINT_DIR,
    TRT_REPO_DIR,
    TRT_MAX_BATCH_SIZE,
    TRT_RUNTIME_BATCH_SIZE,
    TRT_MAX_INPUT_LEN,
    TRT_MAX_OUTPUT_LEN,
    TRT_DTYPE,
    TRT_KV_FREE_GPU_FRAC,
    TRT_KV_ENABLE_BLOCK_REUSE,
    TRT_AWQ_BLOCK_SIZE,
    TRT_CALIB_SIZE,
    TRT_CALIB_SEQLEN,
)
from .chat import (
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
    CHAT_TEMPLATE_ENABLE_THINKING,
    CACHE_RESET_INTERVAL_SECONDS,
    CACHE_RESET_MIN_SESSION_SECONDS,
)
from .tool import (
    TOOL_LANGUAGE_FILTER,
    TOOL_DECISION_THRESHOLD,
    TOOL_COMPILE,
    TOOL_HISTORY_TOKENS,
    TOOL_MAX_LENGTH,
    TOOL_MICROBATCH_MAX_SIZE,
    TOOL_MICROBATCH_MAX_DELAY_MS,
)
from .models import (
    ALLOWED_BASE_CHAT_MODELS,
    ALLOWED_BASE_MOE_CHAT_MODELS,
    ALLOWED_CHAT_MODELS,
    ALLOWED_VLLM_QUANT_CHAT_MODELS,
    ALLOWED_TRT_QUANT_CHAT_MODELS,
    ALLOWED_TOOL_MODELS,
)
from .priorities import (
    CHAT_REQUEST_PRIORITY,
    TOOL_REQUEST_PRIORITY,
    WARM_REQUEST_PRIORITY,
)
from .quantization import (
    SUPPORTED_ENGINES,
    TRT_FP8_SM_ARCHS,
    LOWBIT_QUANTIZATIONS,
    normalize_engine,
)
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
    WS_CLOSE_IDLE_REASON,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)


# Lazy imports for helper functions to avoid circular imports
_helpers_cache = None


def _get_helper_functions():
    """Lazy import helper functions to avoid circular imports."""
    global _helpers_cache
    if _helpers_cache is not None:
        return _helpers_cache
    
    from src.helpers.runtime import configure_runtime_env
    from src.helpers.validation import validate_env, _allow_prequantized_override
    from src.helpers.models import (
        is_valid_model,
        is_classifier_model,
        is_moe_model,
        get_all_base_chat_models,
        get_allowed_chat_models,
        is_local_model_path,
    )
    from src.helpers.quantization import (
        classify_prequantized_model,
        classify_trt_prequantized_model,
        is_awq_model_name,
        is_trt_awq_model_name,
        is_trt_prequantized_model,
        gpu_supports_fp8,
        map_quant_mode_to_trt,
    )
    
    _helpers_cache = {
        'configure_runtime_env': configure_runtime_env,
        'validate_env': validate_env,
        '_allow_prequantized_override': _allow_prequantized_override,
        '_is_valid_model': is_valid_model,
        'is_classifier_model': is_classifier_model,
        'is_moe_model': is_moe_model,
        'get_all_base_chat_models': get_all_base_chat_models,
        'get_allowed_chat_models': get_allowed_chat_models,
        'is_local_model_path': is_local_model_path,
        'classify_prequantized_model': classify_prequantized_model,
        'classify_trt_prequantized_model': classify_trt_prequantized_model,
        'is_awq_model_name': is_awq_model_name,
        'is_trt_awq_model_name': is_trt_awq_model_name,
        'is_trt_prequantized_model': is_trt_prequantized_model,
        'gpu_supports_fp8': gpu_supports_fp8,
        'map_quant_mode_to_trt': map_quant_mode_to_trt,
    }
    return _helpers_cache


def __getattr__(name):
    """Lazy attribute access for helper functions."""
    helper_names = {
        'configure_runtime_env', 'validate_env', '_allow_prequantized_override',
        '_is_valid_model', 'is_classifier_model', 'is_moe_model',
        'get_all_base_chat_models', 'get_allowed_chat_models', 'is_local_model_path',
        'classify_prequantized_model', 'classify_trt_prequantized_model',
        'is_awq_model_name', 'is_trt_awq_model_name', 'is_trt_prequantized_model',
        'gpu_supports_fp8', 'map_quant_mode_to_trt',
    }
    if name in helper_names:
        return _get_helper_functions()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _run_startup_validation():
    """Run model validation checks at startup."""
    helpers = _get_helper_functions()
    _is_valid_model = helpers['_is_valid_model']
    _allow_prequantized_override = helpers['_allow_prequantized_override']
    is_classifier_model = helpers['is_classifier_model']
    is_local_model_path = helpers['is_local_model_path']
    is_awq_model_name = helpers['is_awq_model_name']
    
    if DEPLOY_CHAT and not _is_valid_model(CHAT_MODEL, ALLOWED_CHAT_MODELS, "chat"):
        if not _allow_prequantized_override(CHAT_MODEL, "chat"):
            raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")

    if DEPLOY_TOOL:
        # Tool models must be classifiers
        if not is_classifier_model(TOOL_MODEL):
            raise ValueError("TOOL_MODEL must be a classifier model; vLLM tool engines are no longer supported")
        # Only validate against allowlist for HuggingFace models, not local paths
        if not is_local_model_path(TOOL_MODEL) and TOOL_MODEL not in ALLOWED_TOOL_MODELS:
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


# Run startup validation (deferred to avoid circular imports)
_run_startup_validation()


__all__ = [
    "configure_runtime_env",
    "validate_env",
    # deploy
    "DEPLOY_MODELS",
    "DEPLOY_CHAT",
    "DEPLOY_TOOL",
    "CHAT_MODEL",
    "TOOL_MODEL",
    # gpu
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "GPU_SM_ARCH",
    # engine
    "INFERENCE_ENGINE",
    "QUANTIZATION",
    "CHAT_QUANTIZATION",
    "SUPPORTED_ENGINES",
    # trt
    "TRT_ENGINE_DIR",
    "TRT_CHECKPOINT_DIR",
    "TRT_REPO_DIR",
    "TRT_MAX_BATCH_SIZE",
    "TRT_RUNTIME_BATCH_SIZE",
    "TRT_MAX_INPUT_LEN",
    "TRT_MAX_OUTPUT_LEN",
    "TRT_DTYPE",
    "TRT_KV_FREE_GPU_FRAC",
    "TRT_KV_ENABLE_BLOCK_REUSE",
    "TRT_AWQ_BLOCK_SIZE",
    "TRT_CALIB_SIZE",
    "TRT_CALIB_SEQLEN",
    # chat
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "CACHE_RESET_INTERVAL_SECONDS",
    "CACHE_RESET_MIN_SESSION_SECONDS",
    # tool
    "TOOL_LANGUAGE_FILTER",
    "TOOL_DECISION_THRESHOLD",
    "TOOL_COMPILE",
    "TOOL_HISTORY_TOKENS",
    "TOOL_MAX_LENGTH",
    "TOOL_MICROBATCH_MAX_SIZE",
    "TOOL_MICROBATCH_MAX_DELAY_MS",
    # models/validation
    "ALLOWED_BASE_CHAT_MODELS",
    "ALLOWED_BASE_MOE_CHAT_MODELS",
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_VLLM_QUANT_CHAT_MODELS",
    "ALLOWED_TRT_QUANT_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "is_classifier_model",
    "is_moe_model",
    "get_all_base_chat_models",
    "get_allowed_chat_models",
    "is_local_model_path",
    # quantization helpers
    "TRT_FP8_SM_ARCHS",
    "LOWBIT_QUANTIZATIONS",
    "normalize_engine",
    "is_awq_model_name",
    "is_trt_awq_model_name",
    "is_trt_prequantized_model",
    "gpu_supports_fp8",
    "map_quant_mode_to_trt",
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
    "WS_CLOSE_IDLE_REASON",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    # priorities
    "CHAT_REQUEST_PRIORITY",
    "TOOL_REQUEST_PRIORITY",
    "WARM_REQUEST_PRIORITY",
]
