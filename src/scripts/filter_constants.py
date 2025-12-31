"""Constants for log filtering.

Centralized constants for progress bar groups and other filter settings.
This module is separate from the filters package to avoid triggering
filter initialization when only constants are needed.

Note: TRTLLM_NOISE_PATTERNS is the canonical source; src/config/patterns.py
imports from here for backward compatibility.
"""

from __future__ import annotations

import re

# ============================================================================
# HUGGINGFACE PROGRESS BAR GROUPS
# ============================================================================

# Download-related progress bar groups in huggingface_hub
HF_DOWNLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.http_get",           # Standard downloads (snapshot_download/hf_hub_download)
    "huggingface_hub.xet_get",            # Xet-accelerated downloads
    "huggingface_hub.snapshot_download",  # Parallel snapshot fetch progress
)

# Upload-related progress bar groups in huggingface_hub
HF_UPLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.lfs_upload",         # LFS file uploads
    "huggingface_hub.hf_file_system",     # HfFileSystem operations
    "huggingface_hub.hf_api",             # HfApi upload methods
)

# All progress bar groups combined
HF_ALL_GROUPS: tuple[str, ...] = HF_DOWNLOAD_GROUPS + HF_UPLOAD_GROUPS


# ============================================================================
# TRTLLM LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing TensorRT-LLM and modelopt log noise during quantization
TRTLLM_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[TensorRT-LLM].*TensorRT LLM version", re.IGNORECASE),
    re.compile(r"`?torch_dtype`?\s*(is\s+)?deprecated", re.IGNORECASE),
    re.compile(r"Registered <class 'transformers\.models\..+'> to _QuantAttention", re.IGNORECASE),
    re.compile(r"Inserted \d+ quantizers", re.IGNORECASE),
    re.compile(r"Caching activation statistics", re.IGNORECASE),
    re.compile(r"Searching .*parameters", re.IGNORECASE),
    re.compile(r"Loading extension modelopt", re.IGNORECASE),
    re.compile(r"Loaded extension modelopt", re.IGNORECASE),
    re.compile(r"current rank:\s*\d+,\s*tp rank:\s*\d+,\s*pp rank:\s*\d+", re.IGNORECASE),
)

