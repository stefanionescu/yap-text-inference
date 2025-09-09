import json
import os
from typing import Optional

from vllm.config import KVTransferConfig
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
TOOL_GPU_FRAC = _frac_from_gib(os.getenv("TOOL_GPU_GIB"), float(os.getenv("TOOL_GPU_FRAC", "0.18")))

KV_DTYPE = os.getenv("KV_DTYPE", "fp8")  # 'fp8' or 'int8'

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "4096"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "2048"))

STREAM_RATE_TOKS_PER_S = float(os.getenv("STREAM_RATE_TOKS_PER_S", "10"))

USE_LMCACHE = os.getenv("USE_LMCACHE", "1") == "1"
LMCACHE_REDIS_URI = os.getenv("LMCACHE_REDIS_URI", "").strip()

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

def make_kv_transfer_config() -> Optional[KVTransferConfig]:
    if not USE_LMCACHE:
        return None
    kv_cfg = {}
    if LMCACHE_REDIS_URI:
        kv_cfg["redis_uri"] = LMCACHE_REDIS_URI
    cfg_file = os.getenv("LMCACHE_CONFIG_FILE", "").strip()
    if cfg_file:
        kv_cfg["config_file"] = cfg_file

    return KVTransferConfig(
        kv_connector="LMCacheConnectorV1",
        kv_connector_module_path="lmcache.integration.vllm.lmcache_connector_v1",
        kv_role="kv_both",
        kv_config=kv_cfg or None,
    )


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:
    speculative = None
    if is_chat and ENABLE_SPECULATIVE:
        # vLLM 0.10.1.x expects a speculator name under "model" for built-in methods
        speculative = {
            "model": "ngram",
            "method": "ngram",  # optional but harmless for newer validators
            "num_speculative_tokens": NUM_SPECULATIVE_TOKENS,
        }

    return AsyncEngineArgs(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        enforce_eager=True,
        enable_chunked_prefill=True,
        speculative_config=speculative,
        kv_transfer_config=make_kv_transfer_config(),
    )

