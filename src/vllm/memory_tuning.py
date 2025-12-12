"""GPU memory heuristics and batching utilities."""

from __future__ import annotations

import os
from typing import Any

from src.config.limits import (
    BATCH_SCALE_GPU_FRAC_CAP,
    BATCH_SCALE_MIN_RATIO,
    BATCH_SCALE_MIN_SEQS,
    BATCH_SCALE_MIN_TOKENS,
    MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR,
    MAX_NUM_SEQS_ALLOCATION_RATIO_MAX,
    MAX_NUM_SEQS_ALLOCATION_RATIO_MIN,
    MAX_NUM_SEQS_BASELINE,
    MAX_NUM_SEQS_BASELINE_LARGE,
    MAX_NUM_SEQS_BASELINE_MEDIUM,
    MAX_NUM_SEQS_BASELINE_SMALL,
    MAX_NUM_SEQS_BASELINE_XLARGE,
    MAX_NUM_SEQS_GPU_THRESHOLD_LARGE,
    MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM,
    MAX_NUM_SEQS_GPU_THRESHOLD_SMALL,
    MAX_NUM_SEQS_MAX_RESOLVED,
    MAX_NUM_SEQS_MEMORY_OPT_BASELINE,
    MAX_NUM_SEQS_MIN_FLOOR,
)

__all__ = [
    "auto_max_num_seqs",
    "configure_kv_cache",
    "get_max_num_seqs_override",
    "read_cuda_memory_snapshot",
    "scale_batching_limits",
]

_CUDA_MEM_WARNING_EMITTED = False
_KV_DTYPE_WARNING_EMITTED = False


def read_cuda_memory_snapshot() -> tuple[int, int] | None:
    """Return (free_bytes, total_bytes) for the current CUDA device."""
    global _CUDA_MEM_WARNING_EMITTED
    try:
        import torch  # local import to avoid hard dependency at module import time
    except Exception as exc:  # noqa: BLE001
        if not _CUDA_MEM_WARNING_EMITTED:
            print(f"[config] Warning: torch unavailable for CUDA mem introspection ({exc})")
            _CUDA_MEM_WARNING_EMITTED = True
        return None

    if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
        return None

    try:
        device_index = torch.cuda.current_device() if torch.cuda.is_initialized() else 0
        with torch.cuda.device(device_index):
            free_bytes, total_bytes = torch.cuda.mem_get_info()
        return int(free_bytes), int(total_bytes)
    except Exception as exc:  # noqa: BLE001
        if not _CUDA_MEM_WARNING_EMITTED:
            print(f"[config] Warning: unable to read torch.cuda.mem_get_info ({exc})")
            _CUDA_MEM_WARNING_EMITTED = True
        return None


def scale_batching_limits(
    *,
    max_tokens: int,
    max_seqs: int | None,
    gpu_frac: float,
    engine_role: str,
) -> tuple[int, int | None]:
    """Shrink batching knobs when available memory is below the target budget."""
    snapshot = read_cuda_memory_snapshot()
    if not snapshot or gpu_frac <= 0:
        return max_tokens, max_seqs

    free_bytes, total_bytes = snapshot
    target_bytes = max(int(total_bytes * min(gpu_frac, BATCH_SCALE_GPU_FRAC_CAP)), 1)
    if free_bytes >= target_bytes:
        return max_tokens, max_seqs

    ratio = max(free_bytes / target_bytes, BATCH_SCALE_MIN_RATIO)
    scaled_tokens = max(BATCH_SCALE_MIN_TOKENS, int(max_tokens * ratio))
    scaled_seqs = None
    if max_seqs is not None:
        scaled_seqs = max(BATCH_SCALE_MIN_SEQS, int(max_seqs * ratio))

    print(
        f"[config] Scaling {engine_role} batching limits to {ratio:.2f}x "
        f"(free {free_bytes / (1024**3):.1f} GiB vs budget {target_bytes / (1024**3):.1f} GiB)"
    )
    return scaled_tokens, scaled_seqs


def get_max_num_seqs_override() -> int | None:
    """Return env-provided max_num_seqs override for the chat engine."""

    keys = [
        "MAX_NUM_SEQS_CHAT",
        "MAX_NUM_SEQS",
    ]
    for key in keys:
        value = os.getenv(key)
        if not value:
            continue
        try:
            parsed = int(value)
        except ValueError:
            continue
        if parsed > 0:
            return parsed
    return None


def auto_max_num_seqs(gpu_frac: float, needs_memory_opt: bool) -> int:
    """Heuristically choose max_num_seqs for the chat engine based on GPU size and allocation."""

    baseline = MAX_NUM_SEQS_BASELINE
    min_floor = MAX_NUM_SEQS_MIN_FLOOR
    if needs_memory_opt:
        baseline = min(baseline, MAX_NUM_SEQS_MEMORY_OPT_BASELINE)

    snapshot = read_cuda_memory_snapshot()
    if snapshot:
        _, total_bytes = snapshot
        total_gib = total_bytes / (1024**3)
        if total_gib < MAX_NUM_SEQS_GPU_THRESHOLD_SMALL:
            baseline = min(baseline, MAX_NUM_SEQS_BASELINE_SMALL)
        elif total_gib < MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM:
            baseline = min(baseline, MAX_NUM_SEQS_BASELINE_MEDIUM)
        elif total_gib < MAX_NUM_SEQS_GPU_THRESHOLD_LARGE:
            baseline = min(baseline, MAX_NUM_SEQS_BASELINE_LARGE)
        else:
            baseline = min(baseline, MAX_NUM_SEQS_BASELINE_XLARGE)

    allocation_ratio = (
        max(MAX_NUM_SEQS_ALLOCATION_RATIO_MIN, min(gpu_frac, MAX_NUM_SEQS_ALLOCATION_RATIO_MAX))
        / MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR
    )
    resolved = int(baseline * allocation_ratio)
    return max(min_floor, min(resolved, MAX_NUM_SEQS_MAX_RESOLVED))


def configure_kv_cache(kwargs: dict[str, Any], kv_dtype: str, use_v1: bool) -> None:
    """Attach the appropriate KV cache controls based on engine mode."""
    global _KV_DTYPE_WARNING_EMITTED
    normalized = kv_dtype.strip().lower()
    if not normalized or normalized == "auto":
        return

    if use_v1:
        if normalized.startswith("fp8"):
            os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")
        else:
            if not _KV_DTYPE_WARNING_EMITTED:
                print(
                    f"[config] Warning: kv_cache_dtype={normalized} is ignored by the V1 engine. "
                    "Set VLLM_USE_V1=0 to use legacy int8/fp8 switches."
                )
                _KV_DTYPE_WARNING_EMITTED = True
        return

    kwargs["kv_cache_dtype"] = normalized
    if normalized.startswith("fp8"):
        kwargs["calculate_kv_scales"] = True
