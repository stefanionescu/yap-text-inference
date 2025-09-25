"""Configuration management for vLLM inference stack."""

import os

# Ensure V1 engine is selected before importing any vLLM modules
os.environ.setdefault("VLLM_USE_V1", "1")

from vllm.engine.arg_utils import AsyncEngineArgs


# ----------------- Environment / Defaults -----------------

CHAT_MODEL = os.getenv("CHAT_MODEL")
TOOL_MODEL = os.getenv("TOOL_MODEL")

CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))

KV_DTYPE = os.getenv("KV_DTYPE", "auto")  # 'auto' (fp16) | 'fp8' | 'int8'
QUANTIZATION = os.getenv("QUANTIZATION")  # Must be explicitly set: 'fp8' | 'gptq_marlin'

# Validate required configuration
if not CHAT_MODEL:
    raise ValueError("CHAT_MODEL environment variable is required")
if not TOOL_MODEL:
    raise ValueError("TOOL_MODEL environment variable is required")
if not QUANTIZATION:
    raise ValueError("QUANTIZATION environment variable is required")
if QUANTIZATION not in ["fp8", "gptq_marlin"]:
    raise ValueError(f"QUANTIZATION must be 'fp8' or 'gptq_marlin', got: {QUANTIZATION}")

# Validate allowed models
ALLOWED_CHAT_MODELS = [
    "SicariusSicariiStuff/Impish_Nemo_12B",
    "SicariusSicariiStuff/Impish_Magic_24B",
    "SicariusSicariiStuff/Wingless_Imp_8B",
    "SicariusSicariiStuff/Impish_Mind_8B",
    "SicariusSicariiStuff/Eximius_Persona_5B",
    "SicariusSicariiStuff/Impish_LLAMA_4B",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B",
    "kyx0r/Neona-12B",
    "w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64", 
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",
    "SicariusSicariiStuff/Impish_Magic_24B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B_GPTQ-4-bit-128"
]
ALLOWED_TOOL_MODELS = [
    "MadeAgents/Hammer2.1-1.5b",
    "MadeAgents/Hammer2.1-3b"
]

if CHAT_MODEL not in ALLOWED_CHAT_MODELS:
    raise ValueError(f"CHAT_MODEL must be one of: {ALLOWED_CHAT_MODELS}, got: {CHAT_MODEL}")
if TOOL_MODEL not in ALLOWED_TOOL_MODELS:
    raise ValueError(f"TOOL_MODEL must be one of: {ALLOWED_TOOL_MODELS}, got: {TOOL_MODEL}")

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5760"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "1536"))

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5–15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

USE_LMCACHE = False  # removed
LMCACHE_REDIS_URI = ""

# History and user limits (approximate tokens)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "3000"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "350"))

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"

# Concurrent toolcall mode: if True, run chat and tool models concurrently (default: False)
CONCURRENT_MODEL_CALL = os.getenv("CONCURRENT_MODEL_CALL", "0") == "1"

# Maximum concurrent WebSocket connections (to protect GPU resources)
MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "24"))

# API Key for authentication (all endpoints except /healthz)
API_KEY = os.getenv("YAP_API_KEY", "yap_token")


# ----------------- Helpers -----------------

def make_kv_transfer_config():
    return None


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:

    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype  
    kv_dtype = (KV_DTYPE or "").strip().lower()  # empty => let vLLM decide

    # Use the validated quantization setting
    quant_value = QUANTIZATION if is_chat else None

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
        # Weight quantization for chat; tools remain unquantized for stability
        quantization=(quant_value if is_chat else None),
        dtype="auto",
        # Enable per-request priorities used by generate(..., priority=...)
        scheduling_policy="priority",
    )
    
    # Only pass kv_cache_dtype if explicitly set AND V1 is off
    # (V1 rejects --kv-cache-dtype and will throw NotImplementedError)
    use_v1 = (os.getenv("VLLM_USE_V1", "1") == "1")
    if (not use_v1) and kv_dtype:
        kwargs["kv_cache_dtype"] = kv_dtype
        # Add KV scale calculation for FP8 KV cache
        if kv_dtype.startswith("fp8"):
            # Enable dynamic k/v scale calculation for FP8 KV cache
            kwargs["calculate_kv_scales"] = True

    if use_v1:
        _kv_transfer = make_kv_transfer_config()
        if _kv_transfer is not None:
            kwargs["kv_transfer_config"] = _kv_transfer

    return AsyncEngineArgs(**kwargs)

