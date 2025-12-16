"""TensorRT-LLM engine implementation.

This package provides the TensorRT-LLM inference backend, using pre-built
TensorRT engines for optimized GPU inference.

TRTEngine:
    The main engine class implementing BaseEngine. Uses compiled TensorRT
    engine files for inference.

Factory Functions:
    get_engine() / get_chat_engine(): Return singleton engine instance
    shutdown_engines(): Clean shutdown of the engine

Key Differences from vLLM:
    - Engines are pre-compiled (not JIT compiled)
    - No periodic cache reset needed (block reuse handles memory)
    - Requires TRT_ENGINE_DIR pointing to compiled engine directory
    - Uses tensorrt_llm library instead of vllm

Configuration:
    TRT_ENGINE_DIR: Path to compiled TensorRT engine directory
    TRT_KV_FREE_GPU_FRAC: GPU memory fraction for KV cache
    TRT_KV_ENABLE_BLOCK_REUSE: Enable KV cache block reuse (default)
"""

from .engine import (
    TRTEngine,
    get_engine,
    get_chat_engine,
    shutdown_engines,
)

__all__ = [
    "TRTEngine",
    "get_engine",
    "get_chat_engine",
    "shutdown_engines",
]

