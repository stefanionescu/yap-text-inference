"""Environment initialization and core configuration values.

Sets critical environment variables and reads primary config from env.
Includes validation of required variables and quantization mode.
"""

import os

from ..utils.env import env_flag


# Ensure V1 engine is selected before importing any vLLM modules
os.environ.setdefault("VLLM_USE_V1", "1")


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

# GPU memory fractions: adjust based on deployment mode
if DEPLOY_CHAT and DEPLOY_TOOL:
    # Both models: split GPU memory
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.71"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.21"))
else:
    # Single model: use most of GPU memory
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.92"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.92"))

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto' (fp16) | 'fp8' | 'int8'
QUANTIZATION = os.getenv("QUANTIZATION")  # Must be explicitly set: 'fp8' | 'gptq' | 'gptq_marlin' | 'awq'
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional override per-engine
TOOL_QUANTIZATION = os.getenv("TOOL_QUANTIZATION")  # Optional override per-engine

# Prefixes used to steer chat behavior around screenshot flows
CHECK_SCREEN_PREFIX = os.getenv("CHECK_SCREEN_PREFIX", "MUST CHECK SCREEN:").strip()
SCREEN_CHECKED_PREFIX = os.getenv("SCREEN_CHECKED_PREFIX", "ON THE SCREEN NOW:").strip()
CHAT_TEMPLATE_ENABLE_THINKING = env_flag("CHAT_TEMPLATE_ENABLE_THINKING", False)


def validate_env() -> None:
    """Validate required configuration once during startup."""
    errors: list[str] = []
    if DEPLOY_CHAT and not CHAT_MODEL:
        errors.append("CHAT_MODEL is required when DEPLOY_MODELS is 'both' or 'chat'")
    if DEPLOY_TOOL and not TOOL_MODEL:
        errors.append("TOOL_MODEL is required when DEPLOY_MODELS is 'both' or 'tool'")
    if not QUANTIZATION:
        errors.append("QUANTIZATION environment variable is required")
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
    "TOOL_QUANTIZATION",
    # prefixes
    "CHECK_SCREEN_PREFIX",
    "SCREEN_CHECKED_PREFIX",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "validate_env",
]
