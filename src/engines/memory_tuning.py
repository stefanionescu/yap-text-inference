"""GPU memory heuristics and batching utilities."""

from __future__ import annotations

import os
from typing import Any

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
    target_bytes = max(int(total_bytes * min(gpu_frac, 0.99)), 1)
    if free_bytes >= target_bytes:
        return max_tokens, max_seqs

    ratio = max(free_bytes / target_bytes, 0.1)
    scaled_tokens = max(64, int(max_tokens * ratio))
    scaled_seqs = None
    if max_seqs is not None:
        scaled_seqs = max(4, int(max_seqs * ratio))

    print(
        "[config] Scaling %s batching limits to %.2fx (free %.1f GiB vs budget %.1f GiB)"
        % (
            engine_role,
            ratio,
            free_bytes / (1024**3),
            target_bytes / (1024**3),
        )
    )
    return scaled_tokens, scaled_seqs


def get_max_num_seqs_override(is_chat: bool) -> int | None:
    """Return env-provided max_num_seqs override for the given engine."""

    keys = [
        "MAX_NUM_SEQS_CHAT" if is_chat else "MAX_NUM_SEQS_TOOL",
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


def auto_max_num_seqs(is_chat: bool, gpu_frac: float, needs_memory_opt: bool) -> int:
    """Heuristically choose max_num_seqs based on GPU size and allocation."""

    baseline = 96 if is_chat else 64
    min_floor = 32 if is_chat else 24
    if needs_memory_opt:
        baseline = min(baseline, 64 if is_chat else 48)

    snapshot = read_cuda_memory_snapshot()
    if snapshot:
        _, total_bytes = snapshot
        total_gib = total_bytes / (1024**3)
        if total_gib < 36:
            baseline = min(baseline, 48 if is_chat else 32)
        elif total_gib < 48:
            baseline = min(baseline, 56 if is_chat else 40)
        elif total_gib < 72:
            baseline = min(baseline, 72 if is_chat else 56)
        else:
            baseline = min(baseline, 112 if is_chat else 80)

    allocation_ratio = max(0.4, min(gpu_frac, 0.95)) / 0.85
    resolved = int(baseline * allocation_ratio)
    return max(min_floor, min(resolved, 128))


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
                    "[config] Warning: kv_cache_dtype=%s is ignored by the V1 engine. "
                    "Set VLLM_USE_V1=0 to use legacy int8/fp8 switches."
                    % normalized
                )
                _KV_DTYPE_WARNING_EMITTED = True
        return

    kwargs["kv_cache_dtype"] = normalized
    if normalized.startswith("fp8"):
        kwargs["calculate_kv_scales"] = True
