"""Quantization constants."""

# Supported inference engines
SUPPORTED_ENGINES: tuple[str, ...] = ("vllm", "trt")

VLLM_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}

# Quantization methods that require float16 dtype
FLOAT16_QUANT_METHODS: frozenset[str] = frozenset({
    "awq",
    "awq_marlin",
    "compressed-tensors",
    "fp8",
})

# Mapping from various quantization labels to vLLM's expected names
QUANT_NAME_MAPPING: dict[str, str] = {
    "awq": "awq_marlin",
    "awq-marlin": "awq_marlin",
    "compressed-tensors": "compressed-tensors",
    "compressedtensors": "compressed-tensors",
    "compressed_tensors": "compressed-tensors",
    "compressed-tensor": "compressed-tensors",
    "autoround": "compressed-tensors",
}

# TRT-specific quantization formats
# - int4_awq: 4-bit AWQ for all models (dense and MoE)
# - fp8: 8-bit FP8 (Hopper H100/H200 sm90, Ada L40S/RTX 40 series sm89)
# - int8_sq: 8-bit SmoothQuant INT8 (Ampere A100 sm80, older GPUs without FP8)
TRT_QUANTIZATIONS: set[str] = {"int4_awq", "fp8", "int8_sq"}

# GPU SM architectures that support native FP8
# - sm89: Ada Lovelace (L40S, RTX 40 series: 4090, 4080, 4070 Ti, 4070, 4060 Ti, 4060)
# - sm90: Hopper (H100, H200)
TRT_FP8_SM_ARCHS: tuple[str, ...] = ("sm89", "sm90")

# Markers in model names that indicate pre-quantized AWQ format
AWQ_MODEL_MARKERS: tuple[str, ...] = (
    "awq",
    "w4a16",
    "compressed-tensors",
    "autoround",
)

# Tokenizer files to copy when pushing quantized models to HuggingFace
# Different models use different tokenizer formats
TOKENIZER_FILES: tuple[str, ...] = (
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "tokenizer.model",  # SentencePiece (LLaMA, Mistral)
    "vocab.json",       # Some models
    "merges.txt",       # BPE models
    "added_tokens.json",
)

# Chat template assets that may not live alongside tokenizer files for all models.
# We upload them separately so TRT-LLM has native chat formatting and default
# generation settings (e.g., eos settings) available at runtime.
CHAT_TEMPLATE_FILES: tuple[str, ...] = (
    "chat_template.jinja",
    "generation_config.json",
)


__all__ = [
    "SUPPORTED_ENGINES",
    "TRT_QUANTIZATIONS",
    "TRT_FP8_SM_ARCHS",
    "VLLM_QUANTIZATIONS",
    "FLOAT16_QUANT_METHODS",
    "QUANT_NAME_MAPPING",
    "AWQ_MODEL_MARKERS",
    "TOKENIZER_FILES",
    "CHAT_TEMPLATE_FILES",
]
