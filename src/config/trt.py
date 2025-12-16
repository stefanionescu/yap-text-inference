"""TensorRT-LLM specific configuration.

These settings are only used when INFERENCE_ENGINE='trt'.
TRT params are derived from existing limits when not explicitly set.
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag
from .gpu import CHAT_GPU_FRAC


# Directory paths
TRT_ENGINE_DIR = os.getenv("TRTLLM_ENGINE_DIR", "")
TRT_CHECKPOINT_DIR = os.getenv("TRT_CHECKPOINT_DIR", "")
TRT_REPO_DIR = os.getenv("TRTLLM_REPO_DIR", "")  # Path to TensorRT-LLM repo for quantization

# Engine build parameters
# These use sensible defaults that match our limits.py values:
# - CHAT_MAX_LEN = 5525 (context window)
# - CHAT_MAX_OUT = 150 (generation limit)
_trt_batch_env = os.getenv("TRT_MAX_BATCH_SIZE")
_trt_input_env = os.getenv("TRT_MAX_INPUT_LEN")
_trt_output_env = os.getenv("TRT_MAX_OUTPUT_LEN")

# Batch size for TRT engine
# NOTE: This is different from MAX_CONCURRENT_CONNECTIONS!
# - TRT_MAX_BATCH_SIZE: max sequences batched in a single forward pass (baked into engine)
# - MAX_CONCURRENT_CONNECTIONS: max WebSocket connections (runtime limit)
#
# TRT_MAX_BATCH_SIZE is REQUIRED when building an engine, but at runtime we read
# the baked-in value from engine metadata. If not set here, we use None to indicate
# it should be read from the engine.
TRT_MAX_BATCH_SIZE: int | None = int(_trt_batch_env) if _trt_batch_env else None

# Runtime batch size override (must be <= engine's baked-in max)
# If set, this is the actual batch size to use at runtime
_trt_runtime_batch = os.getenv("TRT_BATCH_SIZE")
TRT_RUNTIME_BATCH_SIZE: int | None = int(_trt_runtime_batch) if _trt_runtime_batch else None

# Input length: use CHAT_MAX_LEN default (5525)
TRT_MAX_INPUT_LEN = int(_trt_input_env) if _trt_input_env else int(os.getenv("CHAT_MAX_LEN", "5525"))

# Output length: use CHAT_MAX_OUT default (150)
TRT_MAX_OUTPUT_LEN = int(_trt_output_env) if _trt_output_env else int(os.getenv("CHAT_MAX_OUT", "150"))

# Data type for compute
TRT_DTYPE = os.getenv("TRT_DTYPE", "float16")

# KV cache memory management - uses CHAT_GPU_FRAC
TRT_KV_FREE_GPU_FRAC = float(os.getenv("TRT_KV_FREE_GPU_FRAC", str(CHAT_GPU_FRAC)))
TRT_KV_ENABLE_BLOCK_REUSE = env_flag("TRT_KV_ENABLE_BLOCK_REUSE", False)

# AWQ quantization parameters (aligned with vLLM AWQ defaults from calibration.py)
# q_group_size/block_size: 128 matches vLLM AWQ
TRT_AWQ_BLOCK_SIZE = int(os.getenv("TRT_AWQ_BLOCK_SIZE", "128"))
# nsamples: 64 matches vLLM AWQ default
TRT_CALIB_SIZE = int(os.getenv("TRT_CALIB_SIZE", "64"))

# Calibration sequence length: derived from context window
_trt_calib_seqlen_env = os.getenv("TRT_CALIB_SEQLEN")
if _trt_calib_seqlen_env:
    TRT_CALIB_SEQLEN = int(_trt_calib_seqlen_env)
else:
    # Use CHAT_MAX_LEN + CHAT_MAX_OUT as calibration seqlen
    _ctx_len = int(os.getenv("CHAT_MAX_LEN", "5525"))
    _ctx_out = int(os.getenv("CHAT_MAX_OUT", "150"))
    TRT_CALIB_SEQLEN = _ctx_len + _ctx_out


__all__ = [
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
]

