"""Runtime environment initialization for CUDA/vLLM.

This module configures environment variables required for optimal vLLM
performance, including attention backend selection and CUDA settings.
It runs at most once per process unless force=True is passed.

Environment Variables Set:
    VLLM_USE_V1: Enable vLLM V1 engine
    VLLM_ATTENTION_BACKEND: FLASHINFER if available, else XFORMERS
    CUDA_DEVICE_MAX_CONNECTIONS: Set for stability
    PYTORCH_ALLOC_CONF: Enable expandable segments
    KV_DTYPE: Forced to auto if FP8 requested without flashinfer

Control Flags:
    YAP_AUTO_CONFIGURE_ENV: Set to enable auto-configuration at import
    YAP_SKIP_ENV_AUTOCONFIG: Set to skip all auto-configuration
"""

from __future__ import annotations

import os
from typing import Final

from src.helpers.env import env_flag


def _configure_vllm_fp8_kv_cache(kv_dtype: str | None) -> None:
    """Set VLLM_FP8_KV_CACHE_ENABLE for V1 engine when using FP8 KV cache.

    Should be called during engine initialization, not at import time.
    Only applies when VLLM_USE_V1 is enabled (default True).

    Args:
        kv_dtype: KV cache data type from config.
    """
    if not env_flag("VLLM_USE_V1", True):
        return
    kv_lower = (kv_dtype or "").strip().lower()
    if kv_lower.startswith("fp8"):
        os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")


_AUTO_CONFIG_FLAG: Final[str] = "YAP_AUTO_CONFIGURE_ENV"
_SKIP_AUTOCONFIG_FLAG: Final[str] = "YAP_SKIP_ENV_AUTOCONFIG"
_STATE = {"env_configured": False}


# ============================================================================
# Internal Helpers
# ============================================================================


def _apply_env_defaults() -> None:
    """Apply all vLLM-related environment defaults."""
    os.environ.setdefault("VLLM_USE_V1", "1")
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("ENFORCE_EAGER", "0")
    os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))
    os.environ.setdefault("CUDA_DEVICE_MAX_CONNECTIONS", "1")
    os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")


def _select_attention_backend() -> None:
    """Set attention backend and KV dtype safeguards based on availability.

    - Prefer FLASHINFER when importable.
    - If FP8 KV is requested but flashinfer is unavailable, force KV_DTYPE=auto.
    - Use only VLLM_ATTENTION_BACKEND for overrides (no extra env knobs).
    """
    backend_hint = os.getenv("VLLM_ATTENTION_BACKEND")

    try:
        import flashinfer  # noqa: F401, PLC0415

        has_flashinfer = True
    except Exception:
        has_flashinfer = False

    backend = backend_hint.strip().upper() if backend_hint else ("FLASHINFER" if has_flashinfer else "XFORMERS")

    os.environ["VLLM_ATTENTION_BACKEND"] = backend

    # If FP8 KV requested without flashinfer, force auto (fp16)
    if (not has_flashinfer) and (os.getenv("KV_DTYPE") or "auto").lower() == "fp8":
        os.environ["KV_DTYPE"] = "auto"


# ============================================================================
# Public API
# ============================================================================


def configure_runtime_env(*, force: bool = False) -> None:
    """Apply CUDA/vLLM environment defaults exactly once per process.

    Args:
        force: Re-run the configuration even if it has already executed.
    """
    if _STATE["env_configured"] and not force:
        return
    if not force and env_flag(_SKIP_AUTOCONFIG_FLAG, False):
        return

    _apply_env_defaults()
    _select_attention_backend()
    # Configure FP8 KV cache for V1 engine if needed
    _configure_vllm_fp8_kv_cache(os.getenv("KV_DTYPE"))
    _STATE["env_configured"] = True


__all__ = ["configure_runtime_env"]
