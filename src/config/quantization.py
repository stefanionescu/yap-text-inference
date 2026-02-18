"""Quantization constants."""

# Supported inference engines
SUPPORTED_ENGINES: tuple[str, ...] = ("vllm", "trt")

VLLM_QUANTIZATIONS: set[str] = {"awq", "gptq", "gptq_marlin"}

# Quantization methods that require float16 dtype
FLOAT16_QUANT_METHODS: frozenset[str] = frozenset(
    {
        "awq",
        "awq_marlin",
        "compressed-tensors",
        "fp8",
    }
)

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

# All recognized quantization formats across all engines
VALID_QUANT_FORMATS: frozenset[str] = frozenset(VLLM_QUANTIZATIONS | TRT_QUANTIZATIONS | {"int8"})

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

# Config files checked for quantization metadata (ordered by priority)
QUANT_CONFIG_FILENAMES: tuple[str, ...] = (
    "config.json",
    "quantization_config.json",
    "quant_config.json",
    "awq_config.json",
)

# Mapping from config-file quant_method / quant_algo values to generic quantization
# names used by detect_chat_quantization (awq, gptq, fp8, int8).
# Covers both HuggingFace (quant_method) and TRT-LLM checkpoint (quant_algo) formats.
QUANT_CONFIG_METHOD_MAP: dict[str, str] = {
    # HuggingFace quant_method values
    "awq": "awq",
    "gptq": "gptq",
    "gptq_marlin": "gptq",
    "fp8": "fp8",
    "int8": "int8",
    "compressed-tensors": "awq",
    "autoround": "awq",
    # TRT-LLM quant_algo values
    "w4a16_awq": "awq",
    "w4a16": "awq",
    "int4_awq": "awq",
    "int8_sq": "int8",
    "w8a8_sq_per_channel": "int8",
    "w8a8_sq_per_tensor_per_token": "int8",
}

# Keys to search for the quantization method string inside a config dict.
# Covers HuggingFace (quant_method), TRT-LLM (quant_algo), and older formats
# where the top-level "quantization" value is a plain string like "awq".
QUANT_CONFIG_METHOD_KEYS: tuple[str, ...] = ("quant_method", "quantization_method", "quant_algo", "quantization")

# Parent keys that may contain a nested quantization dict (checked in order)
QUANT_CONFIG_PARENT_KEYS: tuple[str, ...] = ("quantization_config", "pretrained_config", "quantization", "quant_config")

# Tokenizer files to copy when pushing quantized models to HuggingFace
# Different models use different tokenizer formats
TOKENIZER_FILES: tuple[str, ...] = (
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "tokenizer.model",  # SentencePiece (LLaMA, Mistral)
    "vocab.json",  # Some models
    "merges.txt",  # BPE models
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
    "VALID_QUANT_FORMATS",
    "TRT_FP8_SM_ARCHS",
    "VLLM_QUANTIZATIONS",
    "FLOAT16_QUANT_METHODS",
    "QUANT_NAME_MAPPING",
    "AWQ_MODEL_MARKERS",
    "QUANT_CONFIG_FILENAMES",
    "QUANT_CONFIG_METHOD_MAP",
    "QUANT_CONFIG_METHOD_KEYS",
    "QUANT_CONFIG_PARENT_KEYS",
    "TOKENIZER_FILES",
    "CHAT_TEMPLATE_FILES",
]
