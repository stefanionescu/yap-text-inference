import json
import os
from typing import Optional

from vllm.engine.arg_utils import AsyncEngineArgs


# ----------------- Environment / Defaults -----------------

CHAT_MODEL = os.getenv("CHAT_MODEL", "recoilme/recoilme-gemma-2-9B-v0.5")
TOOL_MODEL = os.getenv("TOOL_MODEL", "MadeAgents/Hammer2.1-3b")

def _frac_from_gib(gib_str: str | None, fallback_frac: float) -> float:
    if not gib_str:
        return fallback_frac
    try:
        want_gib = float(gib_str)
        import torch
        total_gib = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        frac = want_gib / max(1e-6, total_gib)
        return max(0.05, min(0.95, frac))
    except Exception:
        return fallback_frac

CHAT_GPU_FRAC = _frac_from_gib(os.getenv("CHAT_GPU_GIB"), float(os.getenv("CHAT_GPU_FRAC", "0.75")))
TOOL_GPU_FRAC = _frac_from_gib(os.getenv("TOOL_GPU_GIB"), float(os.getenv("TOOL_GPU_FRAC", "0.20")))

KV_DTYPE = os.getenv("KV_DTYPE", "fp8")  # 'fp8' or 'int8'

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "8192"))
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
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "500"))

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
    kv_dtype = (KV_DTYPE or "").strip().lower()
    if kv_dtype not in ("fp8", "int8"):
        kv_dtype = "fp8"

    # Build kwargs for V1 engine.
    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        enable_prefix_caching=True,
        speculative_config=speculative,
        # FP8 here is weight-only quantization (W8). KV cache remains default per V1.
        quantization="fp8",
        # Also quantize KV cache per env
        kv_cache_dtype=kv_dtype,
    )
    if os.getenv("VLLM_USE_V1", "1") == "1":
        _kv_transfer = make_kv_transfer_config()
        if _kv_transfer is not None:
            kwargs["kv_transfer_config"] = _kv_transfer

    return AsyncEngineArgs(**kwargs)

