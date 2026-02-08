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
from ..helpers.env import resolve_gpu_fracs

# ============================================================================
# GPU Memory Allocation
# ============================================================================
# Partition GPU memory between chat engine and classifier to prevent OOM.
# The chat engine (vLLM/TRT) needs most of the memory for model weights
# and KV cache. The classifier is much smaller but still needs some space.

CHAT_GPU_FRAC, TOOL_GPU_FRAC = resolve_gpu_fracs(DEPLOY_CHAT, DEPLOY_TOOL)

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

# ============================================================================
# SM Architecture to Compute Capability Mapping
# ============================================================================
# Maps SM architecture strings to (compute_capability, architecture_note) tuples.
# Used for README generation and compatibility checks.

SM_COMPUTE_CAPABILITY: dict[str, tuple[str, str]] = {
    "sm80": ("8.0", "Ampere / A100"),
    "sm86": ("8.6", "Ampere / RTX 30 series"),
    "sm89": ("8.9", "Ada Lovelace / RTX 40 series"),
    "sm90": ("9.0", "Hopper / H100"),
    "sm100": ("10.0", "Blackwell / B200"),
}

# Default compute capability info when SM arch is unknown
DEFAULT_COMPUTE_CAPABILITY = ("8.9", "Ada Lovelace+")


__all__ = [
    "CHAT_GPU_FRAC",
    "TOOL_GPU_FRAC",
    "KV_DTYPE",
    "GPU_SM_ARCH",
    "SM_COMPUTE_CAPABILITY",
    "DEFAULT_COMPUTE_CAPABILITY",
]
