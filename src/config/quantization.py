"""Quantization constants."""

# Supported inference engines
SUPPORTED_ENGINES: tuple[str, ...] = ("vllm", "trt")

LOWBIT_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}

# TRT-specific quantization formats
# - int4_awq: 4-bit AWQ for dense models (all GPUs)
# - nvfp4: 4-bit floating point for MoE models (all GPUs)
# - fp8: 8-bit FP8 (Hopper H100 sm90, Ada L40S sm89)
# - int8_sq: 8-bit SmoothQuant INT8 (Ampere A100 sm80, older GPUs without FP8)
TRT_QUANTIZATIONS: set[str] = {"int4_awq", "nvfp4", "fp8", "int8_sq"}

# GPU SM architectures that support native FP8
TRT_FP8_SM_ARCHS: tuple[str, ...] = ("sm89", "sm90")  # L40S, H100

# Markers in model names that indicate pre-quantized AWQ format
AWQ_MODEL_MARKERS: tuple[str, ...] = (
    "awq",
    "w4a16",
    "nvfp4",
    "compressed-tensors",
    "autoround",
)


def normalize_engine(engine: str | None) -> str:
    """Normalize engine name to lowercase, default to 'vllm'.
    
    Kept here since it's needed at config load time by engine.py.
    Also available in src.helpers.quantization.
    """
    if not engine:
        return "vllm"
    lowered = engine.lower()
    if lowered in ("trt", "tensorrt", "trtllm", "tensorrt-llm"):
        return "trt"
    if lowered in ("vllm",):
        return "vllm"
    return "vllm"


__all__ = [
    "SUPPORTED_ENGINES",
    "TRT_QUANTIZATIONS",
    "TRT_FP8_SM_ARCHS",
    "LOWBIT_QUANTIZATIONS",
    "AWQ_MODEL_MARKERS",
    "normalize_engine",
]
