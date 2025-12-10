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
DEPLOY_DUAL = DEPLOY_MODELS == "dual"
DEPLOY_CHAT = DEPLOY_MODELS in ("both", "chat", "dual")
DEPLOY_TOOL = DEPLOY_MODELS in ("both", "tool", "dual")

DUAL_MODEL = os.getenv("DUAL_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")
TOOL_MODEL = os.getenv("TOOL_MODEL")

if DEPLOY_DUAL:
    resolved_dual = DUAL_MODEL or CHAT_MODEL or TOOL_MODEL
    if resolved_dual:
        DUAL_MODEL = resolved_dual
        CHAT_MODEL = resolved_dual
        TOOL_MODEL = resolved_dual

# GPU memory fractions: adjust based on deployment mode
if DEPLOY_CHAT and DEPLOY_TOOL and not DEPLOY_DUAL:
    # Both models: split GPU memory conservatively to leave room for CUDA/NCCL
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
else:
    # Single model: keep ~10% free for runtime overhead
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.90"))

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto' (fp16) | 'fp8' | 'int8'
QUANTIZATION = os.getenv("QUANTIZATION")  # Must be explicitly set: 'fp8' | 'gptq' | 'gptq_marlin' | 'awq'
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional override per-engine
TOOL_QUANTIZATION = os.getenv("TOOL_QUANTIZATION")  # Optional override per-engine

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

# ----------------- Classifier Model Settings -----------------
# These are only used when TOOL_MODEL is a classifier (not autoregressive LLM)
CLASSIFIER_THRESHOLD = float(os.getenv("CLASSIFIER_THRESHOLD", "0.66"))
CLASSIFIER_MAX_LENGTH = int(os.getenv("CLASSIFIER_MAX_LENGTH", "1536"))
CLASSIFIER_COMPILE = env_flag("CLASSIFIER_COMPILE", True)  # Use torch.compile for speedup
CLASSIFIER_HISTORY_TOKENS = int(os.getenv("CLASSIFIER_HISTORY_TOKENS", "1200"))  # User-only history limit


def validate_env() -> None:
    """Validate required configuration once during startup."""
    from .models import is_classifier_model
    
    errors: list[str] = []
    if DEPLOY_DUAL and not DUAL_MODEL:
        errors.append("DUAL_MODEL is required when DEPLOY_MODELS is 'dual'")
    if DEPLOY_CHAT and not CHAT_MODEL:
        errors.append("CHAT_MODEL is required when DEPLOY_MODELS is 'both' or 'chat'")
    if DEPLOY_TOOL and not TOOL_MODEL:
        errors.append("TOOL_MODEL is required when DEPLOY_MODELS is 'both' or 'tool'")
    
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
    "DEPLOY_DUAL",
    "DEPLOY_CHAT",
    "DEPLOY_TOOL",
    "DUAL_MODEL",
    "CHAT_MODEL",
    "TOOL_MODEL",
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "QUANTIZATION",
    "CHAT_QUANTIZATION",
    "TOOL_QUANTIZATION",
    # prefixes
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "CACHE_RESET_INTERVAL_SECONDS",
    "CACHE_RESET_MIN_SESSION_SECONDS",
    "TOOL_LANGUAGE_FILTER",
    # classifier settings
    "CLASSIFIER_THRESHOLD",
    "CLASSIFIER_MAX_LENGTH",
    "CLASSIFIER_COMPILE",
    "CLASSIFIER_HISTORY_TOKENS",
    "validate_env",
]
