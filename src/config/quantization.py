"""Shared helpers for quantization-aware configuration logic."""

LOWBIT_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}


def is_lowbit_quantization(value: str | None) -> bool:
    """Return True when the quantization mode should use low-bit limits."""
    if not value:
        return False
    return value in LOWBIT_QUANTIZATIONS


__all__ = ["LOWBIT_QUANTIZATIONS", "is_lowbit_quantization"]


