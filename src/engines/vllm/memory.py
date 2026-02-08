"""GPU memory heuristics and batching utilities for vLLM."""

from __future__ import annotations

import os
import logging
from typing import Any

from src.helpers.dedupe import warn_once
from src.config.limits import (
    BATCH_SCALE_MIN_SEQS,
    BATCH_SCALE_MIN_RATIO,
    MAX_NUM_SEQS_BASELINE,
    BATCH_SCALE_MIN_TOKENS,
    MAX_NUM_SEQS_MIN_FLOOR,
    BATCH_SCALE_GPU_FRAC_CAP,
    MAX_NUM_SEQS_MAX_RESOLVED,
    MAX_NUM_SEQS_BASELINE_LARGE,
    MAX_NUM_SEQS_BASELINE_SMALL,
    MAX_NUM_SEQS_BASELINE_MEDIUM,
    MAX_NUM_SEQS_BASELINE_XLARGE,
    MAX_NUM_SEQS_GPU_THRESHOLD_LARGE,
    MAX_NUM_SEQS_GPU_THRESHOLD_SMALL,
    MAX_NUM_SEQS_MEMORY_OPT_BASELINE,
    MAX_NUM_SEQS_ALLOCATION_RATIO_MAX,
    MAX_NUM_SEQS_ALLOCATION_RATIO_MIN,
    MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM,
    MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR,
)

logger = logging.getLogger(__name__)

# GPU memory thresholds -> baseline mappings (threshold_gib, baseline_value)
# Ordered from smallest to largest threshold; first match wins
_GPU_BASELINE_TIERS: list[tuple[float, int]] = [
    (MAX_NUM_SEQS_GPU_THRESHOLD_SMALL, MAX_NUM_SEQS_BASELINE_SMALL),
    (MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM, MAX_NUM_SEQS_BASELINE_MEDIUM),
    (MAX_NUM_SEQS_GPU_THRESHOLD_LARGE, MAX_NUM_SEQS_BASELINE_LARGE),
]


def read_cuda_memory_snapshot() -> tuple[int, int] | None:
    """Return (free_bytes, total_bytes) for the current CUDA device."""
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:
        warn_once("cuda_torch_import", f"torch unavailable for CUDA mem introspection ({exc})")
        return None

    if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
        return None

    try:
        device_index = torch.cuda.current_device() if torch.cuda.is_initialized() else 0
        with torch.cuda.device(device_index):
            free_bytes, total_bytes = torch.cuda.mem_get_info()
        return int(free_bytes), int(total_bytes)
    except Exception as exc:
        warn_once("cuda_mem_info", f"unable to read torch.cuda.mem_get_info ({exc})")
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

    logger.info(
        "[config] Scaling %s batching limits to %.2fx (free %.1f GiB vs budget %.1f GiB)",
        engine_role,
        ratio,
        free_bytes / (1024**3),
        target_bytes / (1024**3),
    )
    return scaled_tokens, scaled_seqs


def _resolve_baseline_for_gpu_memory(total_gib: float, current_baseline: int) -> int:
    """Select the appropriate baseline based on GPU memory size."""
    for threshold, tier_baseline in _GPU_BASELINE_TIERS:
        if total_gib < threshold:
            return min(current_baseline, tier_baseline)
    return min(current_baseline, MAX_NUM_SEQS_BASELINE_XLARGE)


def auto_max_num_seqs(gpu_frac: float, needs_memory_opt: bool) -> int:
    """Heuristically choose max_num_seqs for the chat engine based on GPU size."""
    baseline = MAX_NUM_SEQS_BASELINE
    if needs_memory_opt:
        baseline = min(baseline, MAX_NUM_SEQS_MEMORY_OPT_BASELINE)

    snapshot = read_cuda_memory_snapshot()
    if snapshot:
        _, total_bytes = snapshot
        total_gib = total_bytes / (1024**3)
        baseline = _resolve_baseline_for_gpu_memory(total_gib, baseline)

    allocation_ratio = (
        max(MAX_NUM_SEQS_ALLOCATION_RATIO_MIN, min(gpu_frac, MAX_NUM_SEQS_ALLOCATION_RATIO_MAX))
        / MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR
    )
    resolved = int(baseline * allocation_ratio)
    return max(MAX_NUM_SEQS_MIN_FLOOR, min(resolved, MAX_NUM_SEQS_MAX_RESOLVED))


def configure_kv_cache(kwargs: dict[str, Any], kv_dtype: str, use_v1: bool) -> None:
    """Attach the appropriate KV cache controls based on engine mode."""
    normalized = kv_dtype.strip().lower()
    if not normalized or normalized == "auto":
        return

    if use_v1:
        if normalized.startswith("fp8"):
            os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")
            logger.info("[config] V1 engine: FP8 KV cache enabled")
        elif normalized.startswith("int8"):
            warn_once(
                "kv_dtype_int8",
                "V1 engine: INT8 KV cache requested. FlashInfer will use fp16 KV cache.",
                prefix="[config]",
            )
        else:
            warn_once(
                f"kv_dtype_{normalized}",
                f"kv_cache_dtype={normalized} may not be supported by V1 engine.",
            )
        return

    kwargs["kv_cache_dtype"] = normalized
    if normalized.startswith("fp8"):
        kwargs["calculate_kv_scales"] = True


__all__ = [
    "auto_max_num_seqs",
    "configure_kv_cache",
    "read_cuda_memory_snapshot",
    "scale_batching_limits",
]
