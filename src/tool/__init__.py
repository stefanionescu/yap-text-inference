"""Tool package for screenshot intent detection.

This package provides a lightweight tool model for detecting when users
want to take a screenshot. Supports BERT-style and Longformer models.

Architecture:
    ToolAdapter:
        High-level interface that handles:
        - Input formatting (combining history + current utterance)
        - Threshold-based decision (probability -> yes/no)
        - GPU memory limit enforcement

    TorchToolBackend:
        PyTorch inference backend supporting:
        - BERT-style models (DistilBERT, RoBERTa, etc.)
        - Longformer models (for longer context)
        - Optional torch.compile() optimization

    BatchExecutor:
        Micro-batching for efficiency:
        - Accumulates requests for batch_max_delay_ms
        - Runs batches up to batch_max_size
        - Thread-based for non-blocking operation

Configuration (via environment):
    TOOL_MODEL: HuggingFace model path/ID
    TOOL_DECISION_THRESHOLD: Probability threshold for screenshot detection
    TOOL_COMPILE: Whether to use torch.compile()
    TOOL_MAX_LENGTH: Maximum input tokens

Micro-batching parameters (batch size, delay) are hardcoded per model
in src.config.models.TOOL_MODEL_BATCH_CONFIG.

Usage:
    from src.tool import get_tool_adapter

    adapter = get_tool_adapter()  # configured during runtime bootstrap
    user_history = session_handler.get_user_history_text(session_id)
    result = adapter.run_tool_inference(user_utt, user_history)
"""

from __future__ import annotations

from .adapter import ToolAdapter
from .registry import get_tool_adapter, reset_tool_adapter

__all__ = [
    "ToolAdapter",
    "get_tool_adapter",
    "reset_tool_adapter",
]
