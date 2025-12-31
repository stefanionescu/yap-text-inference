"""Tokenizer source inspection and resolution.

This module handles detecting where to load tokenizers from:

1. Local directory with tokenizer.json
2. AWQ quantized models with awq_metadata.json pointing to source
3. HuggingFace remote repos

The TokenizerSource dataclass captures the metadata needed to
decide which loading strategy to use.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TokenizerSource:
    """Metadata about where to load a tokenizer from.
    
    Attributes:
        original_path: The path/repo provided by the user.
        is_local: Whether it's a local directory.
        tokenizer_json_path: Path to tokenizer.json if found.
        awq_metadata_model: Source model from awq_metadata.json if AWQ.
    """
    original_path: str
    is_local: bool
    tokenizer_json_path: str | None
    awq_metadata_model: str | None


@dataclass(slots=True)
class TransformersTarget:
    """Target for loading a transformers tokenizer.
    
    Attributes:
        identifier: HuggingFace repo ID or local path.
        local_only: Whether to restrict to local files only.
    """
    identifier: str
    local_only: bool


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
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                candidate = (meta.get("source_model") or "").strip()
                if candidate:
                    awq_metadata_model = candidate
            except Exception:
                pass

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
    1. If remote repo, use it directly
    2. If local with tokenizer.json, use local path
    3. If AWQ with source model, use source model from HF
    4. Otherwise use local path
    
    Args:
        path_or_repo: Original path or repo.
        source: Inspected source metadata.
        
    Returns:
        TransformersTarget with identifier and local_only flag.
    """
    if not source.is_local:
        return TransformersTarget(path_or_repo, False)
    if source.tokenizer_json_path and os.path.isfile(source.tokenizer_json_path):
        return TransformersTarget(path_or_repo, True)
    if source.awq_metadata_model:
        return TransformersTarget(source.awq_metadata_model, False)
    return TransformersTarget(path_or_repo, True)


__all__ = [
    "TokenizerSource",
    "TransformersTarget",
    "inspect_source",
    "resolve_transformers_target",
]

