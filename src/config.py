"""Configuration management for vLLM inference stack."""

import os
from typing import Optional

# Ensure V1 engine is selected before importing any vLLM modules
os.environ.setdefault("VLLM_USE_V1", "1")

# Centralize backend selection and FP8 safety in Python
def _select_attention_backend() -> None:
    """Set attention backend and KV dtype safeguards based on availability.
    - Prefer FLASHINFER when importable.
    - If FP8 KV is requested but flashinfer is unavailable, force KV_DTYPE=auto.
    """
    has_flashinfer = False
    # Select backend if not set; otherwise detect availability for KV fallback
    if not os.getenv("VLLM_ATTENTION_BACKEND"):
        try:
            import flashinfer  # noqa: F401
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASHINFER")
            has_flashinfer = True
        except Exception:
            os.environ.setdefault("VLLM_ATTENTION_BACKEND", "XFORMERS")
            has_flashinfer = False
    else:
        try:
            import flashinfer  # noqa: F401
            has_flashinfer = True
        except Exception:
            has_flashinfer = False

    # If FP8 KV requested without flashinfer, force auto (fp16)
    if not has_flashinfer:
        if (os.getenv("KV_DTYPE") or "auto").lower() == "fp8":
            os.environ["KV_DTYPE"] = "auto"

_select_attention_backend()

from vllm.engine.arg_utils import AsyncEngineArgs


# ----------------- Environment / Defaults -----------------

DEPLOY_MODELS = (os.getenv("DEPLOY_MODELS", "both") or "both").lower()
DEPLOY_CHAT = DEPLOY_MODELS in ("both", "chat")
DEPLOY_TOOL = DEPLOY_MODELS in ("both", "tool")

CHAT_MODEL = os.getenv("CHAT_MODEL")
TOOL_MODEL = os.getenv("TOOL_MODEL")

# GPU memory fractions: adjust based on deployment mode
if DEPLOY_CHAT and DEPLOY_TOOL:
    # Both models: split GPU memory
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
else:
    # Single model: use most of GPU memory
    CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
    TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.90"))

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto' (fp16) | 'fp8' | 'int8'
QUANTIZATION = os.getenv("QUANTIZATION")  # Must be explicitly set: 'fp8' | 'gptq' | 'gptq_marlin' | 'awq'
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional override per-engine
TOOL_QUANTIZATION = os.getenv("TOOL_QUANTIZATION")  # Optional override per-engine

# Validate required configuration
if DEPLOY_CHAT and not CHAT_MODEL:
    raise ValueError("CHAT_MODEL environment variable is required when deploying chat (DEPLOY_MODELS=both|chat)")
if DEPLOY_TOOL and not TOOL_MODEL:
    raise ValueError("TOOL_MODEL environment variable is required when deploying tool (DEPLOY_MODELS=both|tool)")
if not QUANTIZATION:
    raise ValueError("QUANTIZATION environment variable is required")
if QUANTIZATION not in ["fp8", "gptq", "gptq_marlin", "awq"]:
    raise ValueError(
        f"QUANTIZATION must be 'fp8', 'gptq', 'gptq_marlin', or 'awq', got: {QUANTIZATION}"
    )

# Validate allowed models
ALLOWED_CHAT_MODELS = [
    "kyx0r/Neona-12B",
    "SicariusSicariiStuff/Impish_Nemo_12B",
    "SicariusSicariiStuff/Impish_Magic_24B",
    "SicariusSicariiStuff/Wingless_Imp_8B",
    "SicariusSicariiStuff/Impish_Mind_8B",
    "SicariusSicariiStuff/Eximius_Persona_5B",
    "SicariusSicariiStuff/Impish_LLAMA_4B",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B",
    "w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64", 
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",
    "SicariusSicariiStuff/Impish_Magic_24B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B_GPTQ-4-bit-128"
]
ALLOWED_TOOL_MODELS = [
    "MadeAgents/Hammer2.1-1.5b",
    "MadeAgents/Hammer2.1-3b"
]


def _is_local_model_path(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        return os.path.exists(value)
    except Exception:
        return False

if DEPLOY_CHAT and not (CHAT_MODEL in ALLOWED_CHAT_MODELS or _is_local_model_path(CHAT_MODEL)):
    raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")
if DEPLOY_TOOL and not (TOOL_MODEL in ALLOWED_TOOL_MODELS or _is_local_model_path(TOOL_MODEL)):
    raise ValueError(f"TOOL_MODEL must be one of: {ALLOWED_TOOL_MODELS}, got: {TOOL_MODEL}")

# Additional safety: AWQ requires non-GPTQ chat weights
if QUANTIZATION == "awq" and DEPLOY_CHAT and CHAT_MODEL and "GPTQ" in CHAT_MODEL:
    raise ValueError(
        "For QUANTIZATION=awq, CHAT_MODEL must be a non-GPTQ (float) model. "
        f"Got: {CHAT_MODEL}"
    )

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5160"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "3000"))  # 1450 system + 350 user + 1200 history

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5–15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

# History and user limits (approximate tokens)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "2400"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "350"))

# Tool model specific limits  
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1200"))  # Half of chat history for KV sharing
TOOL_SYSTEM_TOKENS = int(os.getenv("TOOL_SYSTEM_TOKENS", "1450"))  # System prompt + tool response

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"

# Concurrent toolcall mode: if True, run chat and tool models concurrently (default: True)
CONCURRENT_MODEL_CALL = os.getenv("CONCURRENT_MODEL_CALL", "1") == "1"

# Maximum concurrent WebSocket connections (deployment-aware)
if DEPLOY_TOOL and not DEPLOY_CHAT:
    # Tool-only: higher capacity since tool model is lighter
    MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "32"))
elif DEPLOY_CHAT and not DEPLOY_TOOL:
    # Chat-only: standard capacity
    MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "24"))
else:
    # Both models: reduced capacity due to dual-engine overhead
    MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "16"))

# API Key for authentication (all endpoints except /healthz)
API_KEY = os.getenv("YAP_API_KEY", "yap_token")


# ----------------- Helpers -----------------

def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:

    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype  
    kv_dtype = (KV_DTYPE or "").strip().lower()  # empty => let vLLM decide

    # Select per-engine quantization:
    # - If CHAT_QUANTIZATION/TOOL_QUANTIZATION is set, prefer that.
    # - Else default: chat uses QUANTIZATION; tool uses 'awq' only when QUANTIZATION=='awq'.
    if is_chat:
        selected_quant = (CHAT_QUANTIZATION or QUANTIZATION)
    else:
        selected_quant = TOOL_QUANTIZATION or ("awq" if QUANTIZATION == "awq" else None)

    quant_value = selected_quant

    dtype_value = "auto"
    if quant_value in {"awq", "awq_marlin"}:
        dtype_value = "float16"

    # Build kwargs for V1 engine.
    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        # Allow CUDA graphs for better performance
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        enable_prefix_caching=True,  # Always enable prefix caching for performance
        # Weight quantization (None => float weights)
        quantization=quant_value,
        dtype=dtype_value,
        # Enable per-request priorities used by generate(..., priority=...)
        scheduling_policy="priority",
    )
    
    # Special handling for local AWQ models to avoid Hugging Face repo ID validation
    if quant_value == "awq" and _is_local_model_path(model):
        # For local AWQ models, ensure the path is absolute so vLLM treats it as local
        kwargs["model"] = os.path.abspath(model)
    
    # Only pass kv_cache_dtype if explicitly set AND V1 is off
    # (V1 rejects --kv-cache-dtype and will throw NotImplementedError)
    use_v1 = (os.getenv("VLLM_USE_V1", "1") == "1")
    if (not use_v1) and kv_dtype:
        kwargs["kv_cache_dtype"] = kv_dtype
        # Add KV scale calculation for FP8 KV cache
        if kv_dtype.startswith("fp8"):
            # Enable dynamic k/v scale calculation for FP8 KV cache
            kwargs["calculate_kv_scales"] = True

    return AsyncEngineArgs(**kwargs)
