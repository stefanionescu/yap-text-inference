"""Shared helpers for quantization-aware configuration logic."""

LOWBIT_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}
_W4A16_HINTS = ("w4a16", "nvfp4", "compressed-tensors", "autoround")


def is_lowbit_quantization(value: str | None) -> bool:
    """Return True when the quantization mode should use low-bit limits."""
    if not value:
        return False
    return value in LOWBIT_QUANTIZATIONS


def is_awq_model_name(value: str | None) -> bool:
    """Heuristic check for AWQ-style repos."""
    if not value:
        return False
    return "awq" in value.lower() and "/" in value


def is_gptq_model_name(value: str | None) -> bool:
    """Heuristic check for GPTQ repos."""
    if not value:
        return False
    lowered = value.lower()
    return "gptq" in lowered and "/" in value


def has_w4a16_marker(value: str | None) -> bool:
    """Detect llmcompressor-style W4A16 exports."""
    if not value:
        return False
    lowered = value.lower()
    return any(marker in lowered for marker in _W4A16_HINTS)


def classify_prequantized_model(value: str | None) -> str | None:
    """Return 'awq' or 'gptq' when the repo name implies a pre-quantized model."""
    if not value:
        return None
    if is_awq_model_name(value) or has_w4a16_marker(value):
        return "awq"
    if is_gptq_model_name(value):
        return "gptq"
    return None


def is_prequantized_model(value: str | None) -> bool:
    """True when classify_prequantized_model detects a known pre-quant format."""
    return classify_prequantized_model(value) is not None


__all__ = [
    "LOWBIT_QUANTIZATIONS",
    "is_lowbit_quantization",
    "is_awq_model_name",
    "is_gptq_model_name",
    "has_w4a16_marker",
    "classify_prequantized_model",
    "is_prequantized_model",
]


