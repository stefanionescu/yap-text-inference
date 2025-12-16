import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineSettings:
    """TensorRT-LLM engine configuration."""

    trtllm_engine_dir: str = os.getenv("TRTLLM_ENGINE_DIR", "").strip()
    kv_free_gpu_frac: str | None = os.getenv("KV_FREE_GPU_FRAC")
    kv_enable_block_reuse: bool = os.getenv("KV_ENABLE_BLOCK_REUSE", "0") == "1"
