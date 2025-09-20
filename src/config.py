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

# Prefer INT8 KV on pre-Hopper (A100/SM80). 'fp8' KV requires SM90.
KV_DTYPE = os.getenv("KV_DTYPE", "fp8_e5m2")  # prefer fp8_e5m2 on A100; 'auto' to defer
WEIGHT_QUANTIZATION = os.getenv("WEIGHT_QUANTIZATION", "none").strip().lower()

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
    # Detect device capability once per engine args build
    def _is_sm90_or_newer() -> bool:
        try:
            import torch  # noqa: WPS433 (allow local import)
            major, _ = torch.cuda.get_device_capability(0)
            return major >= 9
        except Exception:
            return False
    def _is_sm80() -> bool:
        try:
            import torch
            major, _ = torch.cuda.get_device_capability(0)
            return major == 8
        except Exception:
            return False

    def _engine_fields() -> set:
        try:
            fields = getattr(AsyncEngineArgs, "model_fields", None) or getattr(AsyncEngineArgs, "__fields__", None)
            if isinstance(fields, dict):
                return set(fields.keys())
        except Exception:
            pass
        return set()

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

    fields = _engine_fields()
    # Start with a superset of commonly available args
    raw_kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        enable_prefix_caching=True,
    )
    # Conditionally include speculative only if supported
    if speculative is not None and "speculative_config" in fields:
        raw_kwargs["speculative_config"] = speculative
    # Conditionally include attention backend only if supported
    attn_backend = os.getenv("VLLM_ATTENTION_BACKEND")
    if attn_backend and "attention_backend" in fields:
        raw_kwargs["attention_backend"] = attn_backend
    # Resolve KV cache dtype: prefer fp8_e5m2 on A100; avoid passing unsupported values
    kv = (KV_DTYPE or "").strip().lower()
    resolved_kv: Optional[str] = None
    if kv and kv != "auto":
        if kv == "fp8":
            resolved_kv = "fp8_e5m2" if _is_sm80() else ("fp8_e4m3" if _is_sm90_or_newer() else None)
        elif kv.startswith("fp8_"):
            resolved_kv = kv
        elif kv == "int8":
            # Many vLLM 0.8.x builds do not recognize int8 kv. Skip to avoid validation error.
            resolved_kv = None
    else:
        # Auto: choose fp8_e5m2 on A100 for KV quant; else leave to engine default
        if _is_sm80():
            resolved_kv = "fp8_e5m2"
    if resolved_kv:
        # Always pass for V0; safe for most versions. V1 ignores or validates.
        raw_kwargs["kv_cache_dtype"] = resolved_kv

    # Optional weight-only quantization if supported and requested
    if WEIGHT_QUANTIZATION and WEIGHT_QUANTIZATION != "none" and "quantization" in fields:
        if WEIGHT_QUANTIZATION == "fp8":
            if _is_sm90_or_newer():
                raw_kwargs["quantization"] = "fp8"
        else:
            raw_kwargs["quantization"] = WEIGHT_QUANTIZATION

    # Filter by engine fields to avoid passing unsupported args across versions
    kwargs = {k: v for k, v in raw_kwargs.items() if (v is not None) and (not fields or k in fields)}
    # kv_transfer is a V1 feature; include only if supported
    if "kv_transfer_config" in fields:
        _kv_transfer = make_kv_transfer_config()
        if _kv_transfer is not None:
            kwargs["kv_transfer_config"] = _kv_transfer

    return AsyncEngineArgs(**kwargs)

