"""Tokenizer loading utilities.

This module handles the actual loading of tokenizers from different sources:

1. Local tokenizer.json files using the tokenizers library
2. Transformers AutoTokenizer with fallback strategies

The loading logic includes fallback handling for AWQ quantized models
that may need to fetch the tokenizer from the source model.
"""

from __future__ import annotations

import contextlib
import logging
import os

from tokenizers import Tokenizer

from src.state import TokenizerSource, TransformersTarget

logger = logging.getLogger(__name__)


def load_local_tokenizer(source: TokenizerSource) -> Tokenizer | None:
    """Load a tokenizer from a local tokenizer.json file.

    Args:
        source: Inspected source metadata.

    Returns:
        Loaded Tokenizer instance, or None if not found.
    """
    tokenizer_path = source.tokenizer_json_path
    if not tokenizer_path or not os.path.isfile(tokenizer_path):
        return None
    tok = Tokenizer.from_file(tokenizer_path)
    logger.info("tokenizer: loaded local tokenizer.json at %s", tokenizer_path)
    return tok


def load_transformers_tokenizer(target: TransformersTarget):
    """Load a transformers tokenizer from the specified target.

    Args:
        target: Target with identifier and local_only flag.

    Returns:
        Loaded transformers tokenizer (fast or slow).

    Raises:
        RuntimeError: If transformers is not available.
        Exception: If loading fails.
    """
    try:
        from transformers import AutoTokenizer  # noqa: PLC0415
    except Exception as exc:
        raise RuntimeError(f"Transformers is required for tokenizer fallback: {exc}") from exc

    def _try_load(use_fast: bool):
        return AutoTokenizer.from_pretrained(
            target.identifier,
            use_fast=use_fast,
            trust_remote_code=True,
            local_files_only=target.local_only,
        )

    try:
        tokenizer = _try_load(True)
    except Exception:
        tokenizer = _try_load(False)

    logger.info(
        "tokenizer: loaded transformers tokenizer target=%s local_only=%s",
        target.identifier,
        target.local_only,
    )
    return tokenizer


def load_transformers_with_fallback(
    target: TransformersTarget,
    *,
    original_path: str,
    source: TokenizerSource,
    have_local: bool,
):
    """Load a transformers tokenizer with fallback strategies.

    Tries to load from the target, falling back to:
    1. Local path if target was a remote reference
    2. None if local tokenizer.json is available

    Args:
        target: Primary target to try loading from.
        original_path: Original path provided by user.
        source: Inspected source metadata.
        have_local: Whether a local tokenizer.json was loaded.

    Returns:
        Loaded transformers tokenizer, or None if fallback to local.

    Raises:
        Exception: If loading fails and no local tokenizer available.
    """
    try:
        return load_transformers_tokenizer(target)
    except Exception as exc:
        if target.identifier != original_path and source.is_local:
            fallback = TransformersTarget(original_path, True)
            with contextlib.suppress(Exception):
                tok = load_transformers_tokenizer(fallback)
                logger.info(
                    "tokenizer: fallback load transformers local path=%s",
                    original_path,
                )
                return tok

        if not have_local:
            raise

        logger.warning(
            "tokenizer: transformers load failed target=%s local_only=%s",
            target.identifier,
            target.local_only,
            exc_info=exc,
        )
        return None


__all__ = [
    "load_local_tokenizer",
    "load_transformers_tokenizer",
    "load_transformers_with_fallback",
]
