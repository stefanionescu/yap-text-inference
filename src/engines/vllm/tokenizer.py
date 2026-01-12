"""Tokenizer support helpers for vLLM engine builders."""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from vllm.engine.arg_utils import AsyncEngineArgs

from src.helpers.profiles import get_model_profile
from src.helpers.profiles import normalize_model_id
from src.helpers.log_once import warn_once

logger = logging.getLogger(__name__)

_FIX_MISTRAL_REGEX_PATCH_INSTALLED = False
_FIX_MISTRAL_REGEX_MARKERS: set[str] = set()


def _resolve_tokenizer_kwarg_key() -> str | None:
    """Return the AsyncEngineArgs kwarg that accepts tokenizer kwargs."""
    try:
        params = inspect.signature(AsyncEngineArgs.__init__).parameters
    except (ValueError, TypeError):
        return None
    for candidate in ("tokenizer_kwargs", "tokenizer_init_kwargs"):
        if candidate in params:
            return candidate
    return None


_TOKENIZER_KWARG_KEY = _resolve_tokenizer_kwarg_key()


def inject_tokenizer_kwargs(
    target: dict[str, Any],
    tok_kwargs: dict[str, Any],
    model_identifier: str | None,
) -> None:
    """Attach tokenizer kwargs if the installed vLLM supports them."""
    if not tok_kwargs:
        return
    if _TOKENIZER_KWARG_KEY:
        target[_TOKENIZER_KWARG_KEY] = tok_kwargs
        return
    if _patch_tokenizer(model_identifier, tok_kwargs):
        return

    keys = ", ".join(sorted(tok_kwargs.keys()))
    warn_once(
        "tokenizer_kwargs_unsupported",
        f"vLLM does not expose tokenizer kwargs; skipping tokenizer overrides ({keys or 'unknown keys'}).",
    )


def _patch_tokenizer(model_identifier: str | None, tok_kwargs: dict[str, Any]) -> bool:
    """Best-effort tokenizer monkeypatch for engines lacking tokenizer kwargs."""
    if not tok_kwargs:
        return False

    needs_mistral_fix = tok_kwargs.get("fix_mistral_regex")
    if not needs_mistral_fix:
        return False

    markers: set[str] = set()
    profile = get_model_profile(model_identifier) if model_identifier else None
    if profile:
        for marker in profile.markers:
            normalized = normalize_model_id(marker)
            if normalized:
                markers.add(normalized)

    normalized_identifier = normalize_model_id(model_identifier)
    if normalized_identifier:
        markers.add(normalized_identifier)

    if not markers:
        return False

    return _install_fix_mistral_regex_patch(markers)


def _install_fix_mistral_regex_patch(markers: set[str]) -> bool:
    """Monkeypatch AutoTokenizer to force fix_mistral_regex for specific models."""
    global _FIX_MISTRAL_REGEX_PATCH_INSTALLED, _FIX_MISTRAL_REGEX_MARKERS

    try:
        from transformers import AutoTokenizer
    except Exception as exc:
        warn_once(
            "transformers_import",
            f"transformers not available to patch tokenizer kwargs fallback ({exc}).",
        )
        return False

    markers = {m for m in markers if m}
    if not markers:
        return False

    _FIX_MISTRAL_REGEX_MARKERS.update(markers)

    if _FIX_MISTRAL_REGEX_PATCH_INSTALLED:
        return True

    original = AutoTokenizer.from_pretrained.__func__

    def _patched_from_pretrained(cls, pretrained_model_name_or_path, *args, **kwargs):
        normalized = _normalize_tokenizer_identifier(pretrained_model_name_or_path)
        if normalized and any(marker in normalized for marker in _FIX_MISTRAL_REGEX_MARKERS):
            kwargs.setdefault("fix_mistral_regex", True)
        return original(cls, pretrained_model_name_or_path, *args, **kwargs)

    AutoTokenizer._yap_original_from_pretrained = original
    AutoTokenizer.from_pretrained = classmethod(_patched_from_pretrained)
    _FIX_MISTRAL_REGEX_PATCH_INSTALLED = True
    logger.info(
        "[config] Applied AutoTokenizer monkeypatch for fix_mistral_regex (markers: %s)",
        ", ".join(sorted(_FIX_MISTRAL_REGEX_MARKERS)),
    )
    return True


def _normalize_tokenizer_identifier(candidate: Any) -> str:
    """Best-effort normalization for AutoTokenizer inputs."""
    if candidate is None:
        return ""
    if isinstance(candidate, str | os.PathLike):
        return normalize_model_id(os.fspath(candidate))

    name_or_path = getattr(candidate, "name_or_path", None)
    if isinstance(name_or_path, str):
        return normalize_model_id(name_or_path)

    return normalize_model_id(str(candidate))


__all__ = ["inject_tokenizer_kwargs"]
