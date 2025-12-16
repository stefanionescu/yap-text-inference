"""Helper functions extracted from config modules.

This package contains business logic that was previously mixed with
configuration parameters. Config modules now only contain parameters.
"""

from .models import (
    is_classifier_model,
    is_valid_model,
    is_moe_model,
    get_all_base_chat_models,
    get_allowed_chat_models,
    is_local_model_path,
)
from .quantization import (
    is_lowbit_quantization,
    is_awq_model_name,
    is_gptq_model_name,
    has_w4a16_marker,
    classify_prequantized_model,
    is_prequantized_model,
    is_trt_awq_model_name,
    classify_trt_prequantized_model,
    is_trt_prequantized_model,
    is_valid_engine,
    normalize_engine,
    gpu_supports_fp8,
    map_quant_mode_to_trt,
)
from .model_profiles import (
    get_model_profile,
    model_requires_bfloat16,
    model_requires_fla_runtime,
    model_needs_memory_optimization,
    model_uses_mla,
    get_tokenizer_kwargs,
)
from .awq import (
    TotalLengthPolicy,
    resolve_total_len,
    canonicalize_dataset_name,
    dataset_fallback,
    dataset_key,
    normalize_model_id,
)
from .templates import (
    resolve_template_name,
    compute_license_info,
)
from .runtime import configure_runtime_env
from .validation import validate_env
from .input import (
    normalize_gender,
    is_gender_empty_or_null,
    normalize_personality,
    is_personality_empty_or_null,
)

__all__ = [
    # models
    "is_classifier_model",
    "is_valid_model",
    "is_moe_model",
    "get_all_base_chat_models",
    "get_allowed_chat_models",
    "is_local_model_path",
    # quantization
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
    # model_profiles
    "get_model_profile",
    "model_requires_bfloat16",
    "model_requires_fla_runtime",
    "model_needs_memory_optimization",
    "model_uses_mla",
    "get_tokenizer_kwargs",
    # awq
    "TotalLengthPolicy",
    "resolve_total_len",
    "canonicalize_dataset_name",
    "dataset_fallback",
    "dataset_key",
    "normalize_model_id",
    # templates
    "resolve_template_name",
    "compute_license_info",
    # runtime
    "configure_runtime_env",
    # validation
    "validate_env",
    # input
    "normalize_gender",
    "is_gender_empty_or_null",
    "normalize_personality",
    "is_personality_empty_or_null",
]
