"""TRT engine setup and validation.

This module provides helpers for:
1. Reading engine metadata from JSON config files
2. Building KV cache configuration
3. Validating runtime batch size against engine limits
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from src.config import (
    TRT_KV_FREE_GPU_FRAC,
    TRT_KV_ENABLE_BLOCK_REUSE,
    TRT_RUNTIME_BATCH_SIZE,
)
from src.config.trt import TRT_ENGINE_CONFIG_FILE, TRT_BUILD_METADATA_FILE
from src.helpers.io import read_json_file


logger = logging.getLogger(__name__)


def build_kv_cache_config() -> dict[str, Any]:
    """Build KV cache configuration from environment settings."""
    kv_cfg: dict[str, Any] = {}
    
    if TRT_KV_FREE_GPU_FRAC:
        with contextlib.suppress(ValueError):
            kv_cfg["free_gpu_memory_fraction"] = float(TRT_KV_FREE_GPU_FRAC)
    
    if TRT_KV_ENABLE_BLOCK_REUSE:
        kv_cfg["enable_block_reuse"] = True
    
    return kv_cfg


def read_checkpoint_model_type(engine_dir: str) -> str | None:
    """Read the model_type from the engine's checkpoint config.
    
    TensorRT-LLM 1.2+ needs model_type to identify architecture.
    Falls back to None if not found (TRT-LLM will try to infer from name).
    """
    config = read_json_file(Path(engine_dir) / TRT_ENGINE_CONFIG_FILE)
    if not isinstance(config, dict):
        return None
    
    model_type = config.get("model_type")
    return str(model_type) if model_type else None


def read_engine_max_batch_size(engine_dir: str) -> int | None:
    """Read the engine's baked-in max_batch_size from metadata.
    
    Checks build_metadata.json first, then falls back to config.json.
    Returns None if batch size cannot be determined.
    """
    engine_path = Path(engine_dir)
    
    # Try build_metadata.json first (written by our build script)
    metadata = read_json_file(engine_path / TRT_BUILD_METADATA_FILE)
    if isinstance(metadata, dict):
        batch_size = metadata.get("max_batch_size")
        if batch_size is not None:
            return int(batch_size)
    
    # Fall back to config.json (TRT-LLM engine config)
    config = read_json_file(engine_path / TRT_ENGINE_CONFIG_FILE)
    if isinstance(config, dict):
        build_cfg = config.get("build_config", {})
        batch_size = build_cfg.get("max_batch_size")
        if batch_size is not None:
            return int(batch_size)
    
    return None


def validate_runtime_batch_size(engine_dir: str) -> None:
    """Validate TRT_BATCH_SIZE against engine's baked-in max.
    
    Raises RuntimeError if TRT_BATCH_SIZE exceeds the engine's max.
    Logs a warning if batch size info is unavailable.
    """
    engine_max = read_engine_max_batch_size(engine_dir)
    
    if engine_max is not None:
        logger.info(
            "TRT engine max_batch_size=%d (baked-in at build time)",
            engine_max,
        )
        
        if TRT_RUNTIME_BATCH_SIZE is not None:
            if TRT_RUNTIME_BATCH_SIZE > engine_max:
                raise RuntimeError(
                    f"TRT_BATCH_SIZE ({TRT_RUNTIME_BATCH_SIZE}) exceeds engine's "
                    f"baked-in max_batch_size ({engine_max}). "
                    f"Either reduce TRT_BATCH_SIZE or rebuild the engine with a larger max_batch_size."
                )
            logger.info(
                "TRT_BATCH_SIZE=%d (runtime, <= engine max %d) ✓",
                TRT_RUNTIME_BATCH_SIZE,
                engine_max,
            )
        else:
            logger.info(
                "TRT_BATCH_SIZE not set, will use engine max (%d)",
                engine_max,
            )
    else:
        logger.warning(
            "Could not determine engine's max_batch_size from metadata. "
            "Batch size validation skipped."
        )
        if TRT_RUNTIME_BATCH_SIZE is not None:
            logger.info("TRT_BATCH_SIZE=%d (unvalidated)", TRT_RUNTIME_BATCH_SIZE)


__all__ = [
    "build_kv_cache_config",
    "read_checkpoint_model_type",
    "read_engine_max_batch_size",
    "validate_runtime_batch_size",
]

