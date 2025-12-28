"""Quantization detection and classification helpers."""

# Constants duplicated here to avoid circular imports with config
# These should match src.config.quantization values
SUPPORTED_ENGINES: tuple[str, ...] = ("vllm", "trt")
LOWBIT_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}
TRT_FP8_SM_ARCHS: tuple[str, ...] = ("sm89", "sm90")  # L40S, H100
_W4A16_HINTS = ("w4a16", "compressed-tensors", "autoround")


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


# ----------------- TRT-LLM Specific Detection -----------------
def is_trt_awq_model_name(value: str | None) -> bool:
    """Heuristic check for TRT-AWQ-style repos (contains both 'trt' and 'awq')."""
    if not value:
        return False
    lowered = value.lower()
    return "trt" in lowered and "awq" in lowered and "/" in value


def classify_trt_prequantized_model(value: str | None) -> str | None:
    """Return 'trt_awq' when the repo name implies a TRT pre-quantized model."""
    if not value:
        return None
    if is_trt_awq_model_name(value):
        return "trt_awq"
    return None


def is_trt_prequantized_model(value: str | None) -> bool:
    """True when model is pre-quantized for TRT-LLM."""
    return classify_trt_prequantized_model(value) is not None


def is_valid_engine(engine: str | None) -> bool:
    """Check if the engine is a supported inference engine."""
    if not engine:
        return False
    return engine.lower() in SUPPORTED_ENGINES


def normalize_engine(engine: str | None) -> str:
    """Normalize engine name to lowercase, default to 'vllm'."""
    if not engine:
        return "vllm"
    lowered = engine.lower()
    if lowered in ("trt", "tensorrt", "trtllm", "tensorrt-llm"):
        return "trt"
    if lowered in ("vllm",):
        return "vllm"
    return "vllm"


def gpu_supports_fp8(sm_arch: str | None) -> bool:
    """Check if GPU SM architecture supports native FP8.
    
    FP8 is supported on:
    - Hopper (H100): sm90
    - Ada Lovelace (L40S, RTX 4090): sm89
    
    NOT supported on:
    - Ampere (A100): sm80 - use int8_sq instead
    """
    if not sm_arch:
        return False
    return sm_arch.lower() in TRT_FP8_SM_ARCHS


def map_quant_mode_to_trt(
    quant_mode: str | None,
    sm_arch: str | None = None,
    is_moe: bool = False,
) -> str:
    """Map generic quant mode (4bit/8bit/awq/fp8) to TRT-LLM qformat.
    
    Args:
        quant_mode: Generic quantization mode (4bit, 8bit, awq, fp8, int8_sq)
        sm_arch: GPU SM architecture (sm80, sm89, sm90) - used to select fp8 vs int8_sq
        is_moe: Reserved for compatibility; MoE now uses int4_awq
    
    Returns:
        TRT-LLM qformat string: int4_awq, fp8, or int8_sq
    """
    if not quant_mode:
        return "int4_awq"
    lowered = quant_mode.lower()
    
    # 4-bit modes -> int4_awq for all models
    if lowered in ("4bit", "awq", "int4_awq"):
        return "int4_awq"
    
    # Explicit 8-bit format specified
    if lowered == "fp8":
        return "fp8"
    if lowered in ("int8_sq", "int8"):
        return "int8_sq"
    
    # Generic 8-bit mode -> select based on GPU architecture
    # 8-bit uses fp8 on supported GPUs
    if lowered == "8bit":
        if gpu_supports_fp8(sm_arch):
            return "fp8"
        # A100 (sm80) and older -> use int8_sq (SmoothQuant)
        return "int8_sq"
    
    return "int4_awq"


__all__ = [
    "SUPPORTED_ENGINES",
    "LOWBIT_QUANTIZATIONS", 
    "TRT_FP8_SM_ARCHS",
    "is_lowbit_quantization",
    "is_awq_model_name",
    "is_gptq_model_name",
    "has_w4a16_marker",
    "classify_prequantized_model",
    "is_prequantized_model",
    "is_trt_awq_model_name",
    "classify_trt_prequantized_model",
    "is_trt_prequantized_model",
    "is_valid_engine",
    "normalize_engine",
    "gpu_supports_fp8",
    "map_quant_mode_to_trt",
]
