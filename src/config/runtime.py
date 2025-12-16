"""Runtime environment initialization for CUDA/vLLM.

Use ``configure_runtime_env()`` before touching CUDA/vLLM state when running tests
or standalone scripts; production entrypoints can keep the on-import default.
"""

from __future__ import annotations

import os
from typing import Final

from ..utils.env import env_flag


_AUTO_CONFIG_FLAG: Final[str] = "YAP_AUTO_CONFIGURE_ENV"
_SKIP_AUTOCONFIG_FLAG: Final[str] = "YAP_SKIP_ENV_AUTOCONFIG"
_ENV_CONFIGURED = False


def _select_attention_backend() -> None:
    """Set attention backend and KV dtype safeguards based on availability.
    - Prefer FLASHINFER when importable.
    - If FP8 KV is requested but flashinfer is unavailable, force KV_DTYPE=auto.
    """
    has_flashinfer = False
    # Select backend if not set; otherwise detect availability for KV fallback
    if not os.getenv("VLLM_ATTENTION_BACKEND"):
        try:
            import flashinfer  # type: ignore[import]  # noqa: F401
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASHINFER")
            has_flashinfer = True
        except Exception:
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "XFORMERS")
            has_flashinfer = False
    else:
        try:
            import flashinfer  # type: ignore[import]  # noqa: F401
            has_flashinfer = True
        except Exception:
            has_flashinfer = False

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


# Auto-configure on import unless disabled
if env_flag(_AUTO_CONFIG_FLAG, True):
    configure_runtime_env()


__all__ = ["configure_runtime_env"]

