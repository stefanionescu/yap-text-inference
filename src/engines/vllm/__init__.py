"""vLLM engine implementation.

This package provides the vLLM-based inference backend. The heavy vLLM
dependency is only loaded when this package is actually imported - the
parent engines module defers imports to runtime via function-level imports.

VLLMEngine:
    The main engine class implementing BaseEngine.

VLLMEngineSingleton:
    Singleton manager class for the engine. Instantiated by the central
    registry (src/engines/registry.py), not here.

CacheResetManager:
    Manages cache reset state and the background daemon for periodic
    memory management.

Note: Runtime environment configuration (VLLM_USE_V1, etc.) is applied
lazily when the engine is first created, not at import time.
"""

from __future__ import annotations

from .cache import CacheResetManager
from .setup import configure_runtime_env
from .engine import VLLMEngine
from .factory import VLLMEngineSingleton

__all__ = [
    "CacheResetManager",
    "VLLMEngine",
    "VLLMEngineSingleton",
    "configure_runtime_env",
]
