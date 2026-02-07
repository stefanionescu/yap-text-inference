"""Tokenizer source inspection and resolution.

This module handles detecting where to load tokenizers from:

1. Local directory with tokenizer.json
2. AWQ quantized models with awq_metadata.json pointing to source
3. HuggingFace remote repos

The TokenizerSource dataclass captures the metadata needed to
decide which loading strategy to use.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from src.state import TokenizerSource, TransformersTarget


def inspect_source(path_or_repo: str) -> TokenizerSource:
    """Inspect a path to determine tokenizer source metadata.

    Checks if path is local, looks for tokenizer.json, and
    checks for AWQ metadata with a source model reference.

    Args:
        path_or_repo: Local directory or HuggingFace repo ID.

    Returns:
        TokenizerSource with inspection results.
    """
    try:
        is_local = os.path.exists(path_or_repo)
    except Exception:
        is_local = False

    tokenizer_json_path = os.path.join(path_or_repo, "tokenizer.json") if is_local else None
    awq_metadata_model: str | None = None

    if is_local:
        meta_path = Path(path_or_repo) / "awq_metadata.json"
        if meta_path.is_file():
            with contextlib.suppress(Exception):
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                candidate = (meta.get("source_model") or "").strip()
                if candidate:
                    awq_metadata_model = candidate

    return TokenizerSource(
        original_path=path_or_repo,
        is_local=is_local,
        tokenizer_json_path=tokenizer_json_path,
        awq_metadata_model=awq_metadata_model,
    )


def resolve_transformers_target(
    path_or_repo: str,
    source: TokenizerSource,
) -> TransformersTarget:
    """Determine the best target for loading a transformers tokenizer.

    Priority:
    1. If remote repo, use it directly (HF will cache locally)
    2. If local directory, always use local_only=True

    For local directories (including AWQ quantized models), we enforce
    local_only=True to ensure tokenizers are loaded from the model
    directory itself. This prevents silently fetching from HuggingFace
    when local tokenizer files are missing.

    Args:
        path_or_repo: Original path or repo.
        source: Inspected source metadata.

    Returns:
        TransformersTarget with identifier and local_only flag.
    """
    if not source.is_local:
        # Remote HuggingFace repo - transformers will cache locally
        return TransformersTarget(path_or_repo, False)
    # Local directory - always enforce local-only loading
    return TransformersTarget(path_or_repo, True)


__all__ = [
    "inspect_source",
    "resolve_transformers_target",
]
