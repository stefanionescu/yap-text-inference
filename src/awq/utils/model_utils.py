"""Model-related utilities for AWQ quantization."""

from typing import Any


def resolve_calibration_seqlen(requested: int, model: Any) -> int:
    """Resolve the calibration sequence length based on model config."""
    requested = max(int(requested), 1)
    config = getattr(model, "config", None)

    max_positions = None
    if config is not None:
        candidates = []
        for attr in ("max_position_embeddings", "max_sequence_length"):
            value = getattr(config, attr, None)
            if value is not None:
                candidates.append(int(value))
        if candidates:
            max_positions = max(candidates)

    if max_positions is not None and requested > max_positions:
        print(
            f"[awq] Requested calibration seqlen {requested} exceeds model limit {max_positions}; clamping."
        )
        return max_positions

    return requested
