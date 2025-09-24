import os

# Ensure V1 engine is selected before importing any vLLM modules
os.environ.setdefault("VLLM_USE_V1", "1")

from vllm.engine.arg_utils import AsyncEngineArgs


# ----------------- Environment / Defaults -----------------

CHAT_MODEL = os.getenv("CHAT_MODEL", "SicariusSicariiStuff/Impish_Nemo_12B")
TOOL_MODEL = os.getenv("TOOL_MODEL", "MadeAgents/Hammer2.1-3b")

CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.75"))
TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.20"))

KV_DTYPE = os.getenv("KV_DTYPE", "fp8")  # 'fp8' or 'int8'
QUANTIZATION_DEFAULT = os.getenv("QUANTIZATION", "fp8")  # 'fp8' | 'none' | 'gptq'

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "6144"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "2048"))

# 0 = no throttling (realtime). Only set >0 if you want fake typing.
STREAM_RATE_TOKS_PER_S = float(os.getenv("STREAM_RATE_TOKS_PER_S", "0"))
# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5–15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

USE_LMCACHE = False  # removed
LMCACHE_REDIS_URI = ""

ENABLE_SPECULATIVE = os.getenv("ENABLE_SPECULATIVE", "0") == "1"
NUM_SPECULATIVE_TOKENS = int(os.getenv("NUM_SPECULATIVE_TOKENS", "5"))

# Text processing toggles
TEXTPROC_ENABLE = os.getenv("TEXTPROC_ENABLE", "1") == "1"

# History and user limits (approximate tokens)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "3000"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "350"))

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"


# ----------------- Helpers -----------------

def make_kv_transfer_config():
    return None


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:
    speculative = None
    if is_chat and ENABLE_SPECULATIVE:
        # vLLM 0.10.1.x expects a speculator name under "model" for built-in methods
        speculative = {
            "model": "ngram",
            "method": "ngram",  # optional but harmless for newer validators
            "num_speculative_tokens": NUM_SPECULATIVE_TOKENS,
        }

    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype  
    kv_dtype = (KV_DTYPE or "").strip().lower()  # empty => let vLLM decide

    # Determine weight quantization for chat engine only
    q_env = (os.getenv("QUANTIZATION", QUANTIZATION_DEFAULT) or "").strip().lower()
    quant_value: str | None
    if q_env in ("", "none", "off", "no"):
        quant_value = None
    else:
        # Allow 'fp8' or 'gptq'
        quant_value = "gptq" if q_env == "gptq" else "fp8"

    # Build kwargs for V1 engine.
    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        # Force eager to avoid CUDA graph capture while stabilizing multi-engine concurrency
        enforce_eager=True,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        enable_prefix_caching=(
            False if (kv_dtype.startswith("fp8") and os.getenv("DISABLE_PREFIX_CACHE_FOR_KV_FP8", "1") == "1")
            else True
        ),
        speculative_config=speculative,
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

