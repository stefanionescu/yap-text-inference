"""Runtime environment initialization for CUDA/vLLM."""

from __future__ import annotations

import os
from typing import Final

from .env import env_flag


_AUTO_CONFIG_FLAG: Final[str] = "YAP_AUTO_CONFIGURE_ENV"
_SKIP_AUTOCONFIG_FLAG: Final[str] = "YAP_SKIP_ENV_AUTOCONFIG"
_ENV_CONFIGURED = False


def _select_attention_backend() -> None:
    """Set attention backend and KV dtype safeguards based on availability.
    - Prefer FLASHINFER when importable.
    - If FP8 KV is requested but flashinfer is unavailable, force KV_DTYPE=auto.
    - Use only VLLM_ATTENTION_BACKEND for overrides (no extra env knobs).
    """
    backend_hint = os.getenv("VLLM_ATTENTION_BACKEND")

    try:
        import flashinfer  # type: ignore[import]  # noqa: F401
        has_flashinfer = True
    except Exception:
        has_flashinfer = False

    if backend_hint:
        backend = backend_hint.strip().upper()
    else:
        backend = "FLASHINFER" if has_flashinfer else "XFORMERS"

    os.environ["VLLM_ATTENTION_BACKEND"] = backend

    # If FP8 KV requested without flashinfer, force auto (fp16)
    if not has_flashinfer:
        if (os.getenv("KV_DTYPE") or "auto").lower() == "fp8":
            os.environ["KV_DTYPE"] = "auto"


def configure_runtime_env(*, force: bool = False) -> None:
    """Apply CUDA/vLLM environment defaults exactly once per process.

    Args:
        force: Re-run the configuration even if it has already executed.
    """
    global _ENV_CONFIGURED
    if _ENV_CONFIGURED and not force:
        return
    if not force and env_flag(_SKIP_AUTOCONFIG_FLAG, False):
        return

    # Ensure V1 engine is selected before importing any vLLM modules
    os.environ.setdefault("VLLM_USE_V1", "1")
    # vLLM docs recommend constraining CUDA streams + allocator defaults for stability
    os.environ.setdefault("CUDA_DEVICE_MAX_CONNECTIONS", "1")
    os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")

    _select_attention_backend()
    _ENV_CONFIGURED = True


__all__ = ["configure_runtime_env"]
