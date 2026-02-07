"""Quantization calibration helpers.

Handles calibration dataset resolution and sequence length policies
for quantization processes (AWQ, GPTQ, etc.).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from src.config.calibration import CALIB_DEFAULT_DATASET
from src.config.limits import CHAT_MAX_LEN, CHAT_MAX_OUT
from src.state import TotalLengthPolicy


_CHAT_DEFAULT_TOTAL = int(
    os.getenv("CALIB_CHAT_TOTAL_LEN", str(CHAT_MAX_LEN + CHAT_MAX_OUT))
)
CHAT_TOTAL_POLICY = TotalLengthPolicy(
    kind="chat",
    default_total=_CHAT_DEFAULT_TOTAL,
    len_env="CHAT_MAX_LEN",
    out_env="CHAT_MAX_OUT",
)


def resolve_total_len(requested: int, policy: TotalLengthPolicy) -> int:
    """Convenience wrapper exposing TotalLengthPolicy.resolve()."""
    return policy.resolve(requested)


# ============================================================================
# Dataset helpers
# ============================================================================

_DATASET_ALIASES: Mapping[str, str] = {
    "open-platypus": CALIB_DEFAULT_DATASET,
    "openplatypus": CALIB_DEFAULT_DATASET,
    "wikitext2": "wikitext",
    "wiki_text": "wikitext",
}

_DATASET_FALLBACKS: Mapping[str, str] = {
    "pileval": CALIB_DEFAULT_DATASET,
    "pile_val": CALIB_DEFAULT_DATASET,
    "pile": CALIB_DEFAULT_DATASET,
}


def _dataset_key(name: str | None) -> str:
    raw = (name or "").strip()
    if not raw:
        return CALIB_DEFAULT_DATASET
    return raw.lower().replace("-", "_").replace(" ", "_")


def dataset_key(name: str | None) -> str:
    """Expose normalized dataset keys for logging or comparisons."""
    return _dataset_key(name)


def canonicalize_dataset_name(name: str | None) -> str:
    """Normalize dataset identifiers, respecting alias mappings."""
    key = _dataset_key(name)
    return _DATASET_ALIASES.get(key, key or CALIB_DEFAULT_DATASET)


def dataset_fallback(name: str) -> str | None:
    """Return a fallback dataset when llmcompressor cannot find the requested one."""
    return _DATASET_FALLBACKS.get(_dataset_key(name))


__all__ = [
    "CHAT_TOTAL_POLICY",
    "TotalLengthPolicy",
    "canonicalize_dataset_name",
    "dataset_fallback",
    "dataset_key",
    "resolve_total_len",
]
