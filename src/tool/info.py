"""Model metadata and context-window helpers for tool runtime.

This module inspects HuggingFace config metadata to determine:
1. Model family (Longformer vs BERT-style),
2. Effective tool-history budget clamping rules.
"""

from __future__ import annotations

from typing import Any
from src.state import ToolModelInfo
from transformers import AutoConfig
from collections.abc import Callable


def _load_config(model_path: str) -> Any:
    return AutoConfig.from_pretrained(model_path, trust_remote_code=True)


def resolve_history_token_limit(*, max_length: int, history_tokens: int | None) -> int:
    """Resolve and clamp the history-token budget for tool context."""
    if history_tokens is None:
        return max(1, int(max_length))
    return max(1, min(int(history_tokens), int(max_length)))


def build_model_info(
    model_path: str,
    max_length: int | None,
    *,
    config_loader: Callable[[str], Any] = _load_config,
) -> ToolModelInfo:
    """Inspect the Hugging Face config and produce tool model metadata.

    Reads config.json from the model path/repo to determine:
    - Model type (BERT vs Longformer)
    - Number of classification labels

    Args:
        model_path: HuggingFace model ID or local directory path.
        max_length: Optional maximum sequence length override.
        config_loader: Loader used to fetch model config metadata.

    Returns:
        ToolModelInfo with extracted/configured metadata.
    """
    config = config_loader(model_path)
    config_type = getattr(config, "model_type", "").lower()
    model_type = "longformer" if config_type == "longformer" else "bert"
    resolved_max_length = int(max_length) if max_length is not None else 512
    num_labels = int(getattr(config, "num_labels", 2))
    return ToolModelInfo(
        model_id=model_path,
        model_type=model_type,
        max_length=max(1, resolved_max_length),
        num_labels=num_labels,
    )


__all__ = [
    "resolve_history_token_limit",
    "build_model_info",
]
