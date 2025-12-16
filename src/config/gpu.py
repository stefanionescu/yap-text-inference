"""GPU memory and architecture configuration.

This module manages GPU resource allocation between the chat engine and
tool classifier. When both are deployed on the same GPU, memory is
partitioned to prevent OOM errors.

Memory Allocation Strategy:
    - Both deployed: Chat gets 70%, Tool gets 20%, 10% reserved
    - Chat only: Chat gets 90%
    - Tool only: Tool gets 90%

The remaining memory is reserved for:
    - CUDA runtime overhead
    - Memory fragmentation
    - Temporary allocations

Environment Variables:
    CHAT_GPU_FRAC: Fraction of GPU memory for chat engine (0.0-1.0)
    TOOL_GPU_FRAC: Fraction of GPU memory for classifier (0.0-1.0)
    KV_DTYPE: KV cache data type ('auto', 'fp8', 'int8')
    GPU_SM_ARCH: GPU SM architecture for FP8 support detection
"""

from __future__ import annotations

import os

from .deploy import DEPLOY_CHAT, DEPLOY_TOOL


# ============================================================================
# GPU Memory Allocation
# ============================================================================
# Partition GPU memory between chat engine and classifier to prevent OOM.
# The chat engine (vLLM/TRT) needs most of the memory for model weights
# and KV cache. The classifier is much smaller but still needs some space.

if DEPLOY_CHAT and DEPLOY_TOOL:
    # Shared GPU: conservative allocation to leave headroom
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
else:
    # Single component: maximize memory utilization
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.90"))

# ============================================================================
# KV Cache Configuration
# ============================================================================
# KV cache stores attention states for prefix caching and generation.
# FP8 reduces memory by 50% vs FP16 but requires Ada/Hopper GPUs.

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto'=fp16, 'fp8', 'int8'

# ============================================================================
# GPU Architecture Detection
# ============================================================================
# SM architecture determines FP8 support:
# - sm80 (A100): No native FP8, use INT8 SmoothQuant
# - sm89 (L40S, RTX 4090): Native FP8 support
# - sm90 (H100): Native FP8 support with higher throughput

GPU_SM_ARCH = os.getenv("GPU_SM_ARCH", "")  # e.g., "sm89", "sm90"


__all__ = [
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "GPU_SM_ARCH",
]

