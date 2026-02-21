"""Factory function for creating tool adapter instances.

This module provides a function to create a ToolAdapter instance.
The singleton management is handled by the registry module.
"""

from __future__ import annotations

import logging
from .adapter import ToolAdapter
from transformers import AutoConfig
from src.config.timeouts import TOOL_TIMEOUT_S
from src.config import TOOL_MODEL, TOOL_COMPILE, TOOL_GPU_FRAC, TOOL_DECISION_THRESHOLD, TOOL_MODEL_BATCH_CONFIG
from src.config.tool import (
    TOOL_MAX_LENGTH,
    TOOL_HISTORY_TOKENS,
    TOOL_MAX_LENGTH_CONFIGURED,
    TOOL_HISTORY_TOKENS_CONFIGURED,
)


def create_tool_adapter() -> ToolAdapter:
    """Create a new ToolAdapter instance using config values.

    This function reads configuration from environment variables and
    creates a fresh adapter instance. It does NOT manage singleton state -
    that's the responsibility of the registry module.

    Micro-batching parameters are resolved from the per-model config in
    ``TOOL_MODEL_BATCH_CONFIG``.

    Returns:
        A new ToolAdapter instance configured from environment.
    """
    if not TOOL_MODEL:
        raise ValueError("TOOL_MODEL must be set to initialize the tool adapter.")
    batch_cfg = TOOL_MODEL_BATCH_CONFIG.get(TOOL_MODEL, {})

    if not batch_cfg and TOOL_MODEL:
        try:
            cfg = AutoConfig.from_pretrained(TOOL_MODEL, trust_remote_code=True)
            alt_name = getattr(cfg, "_name_or_path", "")
            if alt_name:
                batch_cfg = TOOL_MODEL_BATCH_CONFIG.get(alt_name, {})
        except Exception:
            logging.getLogger(__name__).debug("Batch config fallback lookup failed", exc_info=True)

    max_length_raw = TOOL_MAX_LENGTH if TOOL_MAX_LENGTH_CONFIGURED else batch_cfg.get("max_length")
    max_length = int(max_length_raw) if max_length_raw is not None else None
    history_max_tokens = TOOL_HISTORY_TOKENS if TOOL_HISTORY_TOKENS_CONFIGURED else None

    return ToolAdapter(
        model_path=TOOL_MODEL,
        threshold=TOOL_DECISION_THRESHOLD,
        compile_model=TOOL_COMPILE,
        max_length=max_length,
        history_max_tokens=history_max_tokens,
        batch_max_size=int(batch_cfg.get("batch_max_size", 3)),
        batch_max_delay_ms=float(batch_cfg.get("batch_max_delay_ms", 10.0)),
        request_timeout_s=TOOL_TIMEOUT_S,
        gpu_memory_frac=TOOL_GPU_FRAC,
    )


__all__ = ["create_tool_adapter"]
