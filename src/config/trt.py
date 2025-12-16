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
# - MAX_CONCURRENT_CONNECTIONS = batch size (must be set by user)
_trt_batch_env = os.getenv("TRT_MAX_BATCH_SIZE")
_trt_input_env = os.getenv("TRT_MAX_INPUT_LEN")
_trt_output_env = os.getenv("TRT_MAX_OUTPUT_LEN")

# Batch size: use MAX_CONCURRENT_CONNECTIONS if TRT_MAX_BATCH_SIZE not set
if _trt_batch_env:
    TRT_MAX_BATCH_SIZE = int(_trt_batch_env)
else:
    _max_conn = os.getenv("MAX_CONCURRENT_CONNECTIONS")
    TRT_MAX_BATCH_SIZE = int(_max_conn) if _max_conn else 16  # fallback for import-time

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
    "TRT_MAX_INPUT_LEN",
    "TRT_MAX_OUTPUT_LEN",
    "TRT_DTYPE",
    "TRT_KV_FREE_GPU_FRAC",
    "TRT_KV_ENABLE_BLOCK_REUSE",
    "TRT_AWQ_BLOCK_SIZE",
    "TRT_CALIB_SIZE",
    "TRT_CALIB_SEQLEN",
]

