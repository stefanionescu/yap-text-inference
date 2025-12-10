"""Environment initialization and core configuration values.

Sets critical environment variables and reads primary config from env.
Includes validation of required variables and quantization mode.
"""

import os

from ..utils.env import env_flag


# Ensure V1 engine is selected before importing any vLLM modules
os.environ.setdefault("VLLM_USE_V1", "1")
# vLLM docs recommend constraining CUDA streams + allocator defaults for stability
os.environ.setdefault("CUDA_DEVICE_MAX_CONNECTIONS", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def _select_attention_backend() -> None:
    """Set attention backend and KV dtype safeguards based on availability.
    - Prefer FLASHINFER when importable.
    - If FP8 KV is requested but flashinfer is unavailable, force KV_DTYPE=auto.
    """
    has_flashinfer = False
    # Select backend if not set; otherwise detect availability for KV fallback
    if not os.getenv("VLLM_ATTENTION_BACKEND"):
        try:
            import flashinfer  # noqa: F401
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASHINFER")
            has_flashinfer = True
        except Exception:
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "XFORMERS")
            has_flashinfer = False
    else:
        try:
            import flashinfer  # noqa: F401
            has_flashinfer = True
        except Exception:
            has_flashinfer = False

    # If FP8 KV requested without flashinfer, force auto (fp16)
    if not has_flashinfer:
        if (os.getenv("KV_DTYPE") or "auto").lower() == "fp8":
            os.environ["KV_DTYPE"] = "auto"


# Apply attention backend selection immediately on import
_select_attention_backend()


# ----------------- Environment / Defaults -----------------

DEPLOY_MODELS = (os.getenv("DEPLOY_MODELS", "both") or "both").lower()
DEPLOY_CHAT = DEPLOY_MODELS in ("both", "chat")
DEPLOY_TOOL = DEPLOY_MODELS in ("both", "tool")

CHAT_MODEL = os.getenv("CHAT_MODEL")
TOOL_MODEL = os.getenv("TOOL_MODEL")

# GPU memory fractions: chat (vLLM) and classifier (PyTorch)
if DEPLOY_CHAT and DEPLOY_TOOL:
    # Leave headroom when both stacks run on the same GPU
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
else:
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.90"))

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto' (fp16) | 'fp8' | 'int8'
QUANTIZATION = os.getenv("QUANTIZATION")  # Must be explicitly set: 'fp8' | 'gptq' | 'gptq_marlin' | 'awq'
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional override for chat

if os.getenv("VLLM_USE_V1", "1") == "1":
    kv_lower = (KV_DTYPE or "").strip().lower()
    if kv_lower.startswith("fp8"):
        os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")

# Prefixes used to steer chat behavior around screenshot flows
DEFAULT_CHECK_SCREEN_PREFIX = os.getenv("CHECK_SCREEN_PREFIX", "MUST CHECK SCREEN:").strip()
DEFAULT_SCREEN_CHECKED_PREFIX = os.getenv("SCREEN_CHECKED_PREFIX", "ON THE SCREEN NOW:").strip()
CHAT_TEMPLATE_ENABLE_THINKING = env_flag("CHAT_TEMPLATE_ENABLE_THINKING", False)

# Cache management defaults
CACHE_RESET_INTERVAL_SECONDS = float(os.getenv("CACHE_RESET_INTERVAL_SECONDS", "600"))
CACHE_RESET_MIN_SESSION_SECONDS = float(os.getenv("CACHE_RESET_MIN_SESSION_SECONDS", "300"))

# Tool language filter: skip tool call if user message is not mostly English
TOOL_LANGUAGE_FILTER = env_flag("TOOL_LANGUAGE_FILTER", True)

# ----------------- Tool Classifier Settings -----------------
# These are only used when TOOL_MODEL is a classifier (not autoregressive LLM)
TOOL_DECISION_THRESHOLD = float(os.getenv("TOOL_DECISION_THRESHOLD", "0.66"))
TOOL_COMPILE = env_flag("TOOL_COMPILE", True)  # Use torch.compile for speedup
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1536"))
TOOL_MAX_LENGTH = int(os.getenv("TOOL_MAX_LENGTH", "1536"))
TOOL_MICROBATCH_MAX_SIZE = int(os.getenv("TOOL_MICROBATCH_MAX_SIZE", "4"))
TOOL_MICROBATCH_MAX_DELAY_MS = float(os.getenv("TOOL_MICROBATCH_MAX_DELAY_MS", "5.0"))
TOOL_USE_ONNX = env_flag("TOOL_USE_ONNX", False)
TOOL_ONNX_DIR = os.getenv("TOOL_ONNX_DIR", "build/classifier_onnx")
TOOL_ONNX_OPSET = int(os.getenv("TOOL_ONNX_OPSET", "17"))


def validate_env() -> None:
    """Validate required configuration once during startup."""
    from .models import is_classifier_model
    
    errors: list[str] = []
    if DEPLOY_CHAT and not CHAT_MODEL:
        errors.append("CHAT_MODEL is required when DEPLOY_MODELS is 'both' or 'chat'")
    if DEPLOY_TOOL and not TOOL_MODEL:
        errors.append("TOOL_MODEL is required when DEPLOY_MODELS is 'both' or 'tool'")
    if DEPLOY_TOOL and TOOL_MODEL and not is_classifier_model(TOOL_MODEL):
        errors.append("TOOL_MODEL must be one of the classifier models (vLLM tool engines are disabled)")
    
    # Quantization is only required when deploying LLMs (not classifiers)
    # Classifier-only mode (DEPLOY_CHAT=False and TOOL_MODEL is classifier) doesn't need quantization
    needs_quantization = DEPLOY_CHAT or (DEPLOY_TOOL and not is_classifier_model(TOOL_MODEL))
    if needs_quantization:
        if not QUANTIZATION:
            errors.append("QUANTIZATION environment variable is required for LLM models")
        elif QUANTIZATION not in {"fp8", "gptq", "gptq_marlin", "awq"}:
            errors.append(
                "QUANTIZATION must be one of 'fp8', 'gptq', 'gptq_marlin', or 'awq'"
            )
    if errors:
        raise ValueError("; ".join(errors))


__all__ = [
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
    # prefixes
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
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
    "TOOL_USE_ONNX",
    "TOOL_ONNX_DIR",
    "TOOL_ONNX_OPSET",
    "validate_env",
]
