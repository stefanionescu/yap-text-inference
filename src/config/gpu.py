"""GPU memory and architecture configuration."""

from __future__ import annotations

import os

from .deploy import DEPLOY_CHAT, DEPLOY_TOOL


# GPU memory fractions: chat (vLLM/TRT) and classifier (PyTorch)
if DEPLOY_CHAT and DEPLOY_TOOL:
    # Leave headroom when both stacks run on the same GPU
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
else:
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.90"))

# KV cache data type: 'auto' (fp16) | 'fp8' | 'int8'
KV_DTYPE = os.getenv("KV_DTYPE", "auto")

# GPU architecture (L40S = sm89, A100 = sm80, H100 = sm90)
GPU_SM_ARCH = os.getenv("GPU_SM_ARCH", "")


__all__ = [
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "GPU_SM_ARCH",
]

