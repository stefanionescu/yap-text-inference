"""TensorRT-LLM engine implementation.

This package provides the TensorRT-LLM inference backend, using pre-built
TensorRT engines for optimized GPU inference.

TRTEngine:
    The main engine class implementing BaseEngine. Uses compiled TensorRT
    engine files for inference.

TRTEngineSingleton:
    Singleton manager class for the engine. Instantiated by the central
    registry (src/engines/registry.py), not here.

Key Differences from vLLM:
    - Engines are pre-compiled (not JIT compiled)
    - No periodic cache reset needed (block reuse handles memory)
    - Requires TRT_ENGINE_DIR pointing to compiled engine directory
    - Uses tensorrt_llm library instead of vllm

Configuration:
    TRT_ENGINE_DIR: Path to compiled TensorRT engine directory
    TRT_KV_FREE_GPU_FRAC: GPU memory fraction for KV cache
"""

from .engine import TRTEngine
from .factory import TRTEngineSingleton

__all__ = [
    "TRTEngine",
    "TRTEngineSingleton",
]
