"""Quantization detection and classification helpers."""

# Constants duplicated here to avoid circular imports with config
# These should match src.config.quantization values
SUPPORTED_ENGINES: tuple[str, ...] = ("vllm", "trt")
LOWBIT_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}
TRT_FP8_SM_ARCHS: tuple[str, ...] = ("sm89", "sm90")  # L40S, H100
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


def gpu_supports_nvfp4(sm_arch: str | None) -> bool:
    """Check if GPU SM architecture supports NVFP4 (4-bit floating point) quantization.
    
    NVFP4 requires native FP4 support:
    - Hopper (H100): sm90 - supported
    - Ada Lovelace (L40S, RTX 4090): sm89 - supported
    - Ampere (A100): sm80 - NOT supported (no native FP4)
    """
    if not sm_arch:
        return False
    # FP4 support is available on sm89+ (same GPUs as FP8)
    return sm_arch.lower() in TRT_FP8_SM_ARCHS


def is_nvfp4_model_name(value: str | None) -> bool:
    """Check if model name indicates NVFP4 quantization."""
    if not value:
        return False
    return "nvfp4" in value.lower()


def validate_nvfp4_gpu_compat(
    model: str | None,
    sm_arch: str | None,
    is_moe: bool = False,
) -> tuple[bool, str]:
    """Validate NVFP4/MoE compatibility with GPU architecture.
    
    Args:
        model: Model name/path
        sm_arch: GPU SM architecture (e.g., sm80, sm89, sm90)
        is_moe: Whether the model is a MoE model
    
    Returns:
        Tuple of (is_valid, error_message).
        If is_valid is True, error_message is empty.
    """
    # Only sm80 (A100) is blocked
    if sm_arch and sm_arch.lower() != "sm80":
        return (True, "")
    
    if not sm_arch:
        # No SM arch detected, can't validate
        return (True, "")
    
    # Check for pre-quantized NVFP4 models
    if is_nvfp4_model_name(model):
        return (
            False,
            f"NVFP4 models cannot run on A100 (sm80). "
            f"NVFP4 requires native FP4 support (L40S sm89, H100 sm90). "
            f"Model: {model}. "
            f"Use vLLM engine or deploy on L40S/H100.",
        )
    
    # Check for MoE models (would use NVFP4 with TRT)
    if is_moe:
        return (
            False,
            f"MoE models cannot use TRT-LLM on A100 (sm80). "
            f"TRT-LLM uses NVFP4 for MoE 4-bit quantization which requires native FP4. "
            f"Model: {model}. "
            f"Use vLLM engine instead or deploy on L40S/H100.",
        )
    
    return (True, "")


def map_quant_mode_to_trt(
    quant_mode: str | None,
    sm_arch: str | None = None,
    is_moe: bool = False,
) -> str:
    """Map generic quant mode (4bit/8bit/awq/fp8) to TRT-LLM qformat.
    
    Args:
        quant_mode: Generic quantization mode (4bit, 8bit, awq, fp8, int8_sq, nvfp4)
        sm_arch: GPU SM architecture (sm80, sm89, sm90) - used to select fp8 vs int8_sq
        is_moe: Whether the model is a Mixture of Experts model
    
    Returns:
        TRT-LLM qformat string: int4_awq, nvfp4, fp8, or int8_sq
        
    Note:
        For MoE models, 4-bit quantization uses NVFP4 (4-bit floating point)
        instead of INT4 AWQ. This provides better quality for sparse expert
        layers that don't benefit from AWQ's activation-aware approach.
    """
    if not quant_mode:
        return "nvfp4" if is_moe else "int4_awq"
    lowered = quant_mode.lower()
    
    # Explicit NVFP4 request
    if lowered == "nvfp4":
        return "nvfp4"
    
    # 4-bit modes -> nvfp4 for MoE, int4_awq for dense models
    if lowered in ("4bit", "awq", "int4_awq"):
        return "nvfp4" if is_moe else "int4_awq"
    
    # Explicit 8-bit format specified
    if lowered == "fp8":
        return "fp8"
    if lowered in ("int8_sq", "int8"):
        return "int8_sq"
    
    # Generic 8-bit mode -> select based on GPU architecture
    # For both MoE and dense models, 8-bit uses fp8 on supported GPUs
    if lowered == "8bit":
        if gpu_supports_fp8(sm_arch):
            return "fp8"
        # A100 (sm80) and older -> use int8_sq (SmoothQuant)
        return "int8_sq"
    
    return "nvfp4" if is_moe else "int4_awq"


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
    "gpu_supports_nvfp4",
    "is_nvfp4_model_name",
    "validate_nvfp4_gpu_compat",
    "map_quant_mode_to_trt",
]
