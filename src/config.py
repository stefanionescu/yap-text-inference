import json
import os
from typing import Optional

from vllm.config import KVTransferConfig
from vllm.engine.arg_utils import AsyncEngineArgs


# ----------------- Environment / Defaults -----------------

CHAT_MODEL = os.getenv("CHAT_MODEL", "recoilme/recoilme-gemma-2-9B-v0.5")
DRAFT_MODEL = os.getenv("DRAFT_MODEL", "MadeAgents/Hammer2.1-3b")

CHAT_GPU_FRAC = float(os.getenv("CHAT_GPU_FRAC", "0.82"))
TOOL_GPU_FRAC = float(os.getenv("TOOL_GPU_FRAC", "0.14"))

KV_DTYPE = os.getenv("KV_DTYPE", "fp8")  # 'fp8' or 'int8'

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "7168"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))

STREAM_RATE_TOKS_PER_S = float(os.getenv("STREAM_RATE_TOKS_PER_S", "10"))

USE_LMCACHE = os.getenv("USE_LMCACHE", "1") == "1"
LMCACHE_REDIS_URI = os.getenv("LMCACHE_REDIS_URI", "").strip()

ENABLE_SPECULATIVE = os.getenv("ENABLE_SPECULATIVE", "1") == "1"
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

    return KVTransferConfig(
        kv_connector="LMCacheConnectorV1Dynamic",
        kv_role="kv_both",
        kv_config=kv_cfg or None,
        # If your vLLM build requires module path, uncomment below:
        # kv_connector_module_path="lmcache.integration.vllm.lmcache_connector_v1",
    )


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:
    speculative_config = None
    if is_chat and ENABLE_SPECULATIVE:
        speculative_config = json.dumps(
            {
                "draft_model": DRAFT_MODEL,
                "num_speculative_tokens": NUM_SPECULATIVE_TOKENS,
                "disable_by_batch_size": 128,
            }
        )

    return AsyncEngineArgs(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        kv_cache_dtype=KV_DTYPE,
        enforce_eager=True,
        enable_chunked_prefill=True,
        speculative_config=speculative_config,
        kv_transfer_config=make_kv_transfer_config(),
    )


