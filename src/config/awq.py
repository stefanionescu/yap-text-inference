"""Centralized configuration helpers for AWQ-specific logic."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from .limits import CHAT_MAX_LEN, CHAT_MAX_OUT, TOOL_MAX_LEN, TOOL_MAX_OUT
from .models import ALLOWED_TOOL_MODELS


def _read_int_env(name: str) -> int | None:
    """Parse an environment value as int, returning None on missing/invalid."""
    raw = os.getenv(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class TotalLengthPolicy:
    """Represents how to compute minimum total sequence length for a model."""

    kind: str
    default_total: int
    len_env: str
    out_env: str

    def resolve(self, requested: int) -> int:
        """Return the minimum seq len respecting env overrides and defaults."""
        requested = max(int(requested), 1)
        total = 0
        max_len = _read_int_env(self.len_env)
        max_out = _read_int_env(self.out_env)
        if max_len is not None:
            total += max(max_len, 0)
        if max_out is not None:
            total += max(max_out, 0)
        floor = total if total > 0 else self.default_total
        return max(requested, floor)


_CHAT_DEFAULT_TOTAL = int(
    os.getenv("AWQ_CHAT_TOTAL_LEN", str(CHAT_MAX_LEN + CHAT_MAX_OUT))
)
_TOOL_DEFAULT_TOTAL = int(
    os.getenv("AWQ_TOOL_TOTAL_LEN", str(TOOL_MAX_LEN + TOOL_MAX_OUT))
)

CHAT_TOTAL_POLICY = TotalLengthPolicy(
    kind="chat",
    default_total=_CHAT_DEFAULT_TOTAL,
    len_env="CHAT_MAX_LEN",
    out_env="CHAT_MAX_OUT",
)

TOOL_TOTAL_POLICY = TotalLengthPolicy(
    kind="tool",
    default_total=_TOOL_DEFAULT_TOTAL,
    len_env="TOOL_MAX_LEN",
    out_env="TOOL_MAX_OUT",
)


def resolve_total_len(requested: int, policy: TotalLengthPolicy) -> int:
    """Convenience wrapper exposing TotalLengthPolicy.resolve()."""
    return policy.resolve(requested)


# ------------------------- Dataset helpers ------------------------- #

AWQ_DEFAULT_DATASET = os.getenv("AWQ_CALIB_DATASET_DEFAULT", "open_platypus")

_DATASET_ALIASES: Mapping[str, str] = {
    "open-platypus": AWQ_DEFAULT_DATASET,
    "openplatypus": AWQ_DEFAULT_DATASET,
    "wikitext2": "wikitext",
    "wiki_text": "wikitext",
}

_DATASET_FALLBACKS: Mapping[str, str] = {
    "pileval": AWQ_DEFAULT_DATASET,
    "pile_val": AWQ_DEFAULT_DATASET,
    "pile": AWQ_DEFAULT_DATASET,
}


def _dataset_key(name: str | None) -> str:
    raw = (name or "").strip()
    if not raw:
        return AWQ_DEFAULT_DATASET
    return raw.lower().replace("-", "_").replace(" ", "_")


def dataset_key(name: str | None) -> str:
    """Expose normalized dataset keys for logging or comparisons."""
    return _dataset_key(name)


def canonicalize_dataset_name(name: str | None) -> str:
    """Normalize dataset identifiers, respecting alias mappings."""
    key = _dataset_key(name)
    return _DATASET_ALIASES.get(key, key or AWQ_DEFAULT_DATASET)


def dataset_fallback(name: str) -> str | None:
    """Return a fallback dataset when llmcompressor cannot find the requested one."""
    return _DATASET_FALLBACKS.get(_dataset_key(name))

# ----------------------- AWQ markers ------------------------- #

AWQ_MODEL_MARKERS: tuple[str, ...] = (
    "awq",
    "w4a16",
    "nvfp4",
    "compressed-tensors",
    "autoround",
)

# ----------------------- Toolcall markers ------------------------- #


def normalize_model_id(model_id: str | None) -> str:
    """Canonicalize model identifiers for substring comparisons."""
    return (model_id or "").strip().lower()


def _derive_toolcall_markers() -> tuple[str, ...]:
    """Build default tool markers directly from the allowed tool models."""
    candidates: list[str] = []
    for model in ALLOWED_TOOL_MODELS:
        normalized = normalize_model_id(model)
        if not normalized:
            continue
        candidates.append(normalized)
        # Also include the last path segment for robustness with local dirs.
        tail = normalized.rsplit("/", 1)[-1]
        if tail and tail != normalized:
            candidates.append(tail)
    seen: set[str] = set()
    deduped: list[str] = []
    for marker in candidates:
        if marker and marker not in seen:
            deduped.append(marker)
            seen.add(marker)
    return tuple(deduped)


_DEFAULT_TOOLCALL_MARKERS: tuple[str, ...] = _derive_toolcall_markers()


def _load_toolcall_markers() -> tuple[str, ...]:
    env_value = os.getenv("AWQ_TOOLCALL_MARKERS")
    if not env_value:
        return _DEFAULT_TOOLCALL_MARKERS
    values: list[str] = []
    for chunk in env_value.split(","):
        normalized = normalize_model_id(chunk)
        if normalized:
            values.append(normalized)
    return tuple(values) if values else _DEFAULT_TOOLCALL_MARKERS


TOOLCALL_MODEL_MARKERS: tuple[str, ...] = _load_toolcall_markers()


def is_toolcall_model(model_id: str) -> bool:
    """Return True if the identifier matches known toolcall markers."""
    normalized = normalize_model_id(model_id)
    return any(marker in normalized for marker in TOOLCALL_MODEL_MARKERS)


# ----------------------- Model profiles --------------------------- #

@dataclass(frozen=True)
class ModelProfile:
    """Describes special-case requirements for known model families."""

    name: str
    markers: tuple[str, ...]
    requires_bfloat16: bool = False
    requires_fla_runtime: bool = False
    needs_memory_optimization: bool = False
    # Post-quantization config.json overrides (applied after AWQ export)
    config_overrides: Mapping[str, Any] | None = None
    # Tokenizer kwargs to pass to vLLM (e.g., fix_mistral_regex for broken tokenizers)
    tokenizer_kwargs: Mapping[str, Any] | None = None

    def matches(self, identifier: str) -> bool:
        return any(marker in identifier for marker in self.markers)


MODEL_PROFILES: tuple[ModelProfile, ...] = (
    ModelProfile(
        name="gemma3",
        markers=("gemma-3", "gemma3"),
        requires_bfloat16=True,
        needs_memory_optimization=True,
    ),
    ModelProfile(
        name="gemma2",
        markers=("gemma-2", "gemma2", "gemma-27b", "gemma-9b"),
        requires_bfloat16=True,
        needs_memory_optimization=True,
        # NOTE: Some Gemma2 finetunes have tie_word_embeddings=false which breaks vLLM's
        # assertion but works fine otherwise. We don't override it here - see below.
    ),
    ModelProfile(
        name="gemma",
        markers=("gemma",),
        needs_memory_optimization=True,
    ),
    ModelProfile(
        name="kimi-linear",
        markers=("kimi-linear", "kimi_linear"),
        requires_bfloat16=True,
        requires_fla_runtime=True,
    ),
    ModelProfile(
        name="kimi",
        markers=("kimi",),
        requires_fla_runtime=True,
    ),
    # Mistral Small 3.x models have a broken tokenizer regex pattern
    # See: https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503/discussions/84
    ModelProfile(
        name="mistral-small-3-jeffcookio",
        markers=("jeffcookio/mistral-small-3",),
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
)


def get_model_profile(model_identifier: str | None) -> ModelProfile | None:
    """Return the first matching profile for the provided identifier."""
    normalized = normalize_model_id(model_identifier)
    if not normalized:
        return None
    for profile in MODEL_PROFILES:
        if profile.matches(normalized):
            return profile
    return None


def model_requires_bfloat16(model_identifier: str | None) -> bool:
    profile = get_model_profile(model_identifier)
    return bool(profile and profile.requires_bfloat16)


def model_requires_fla_runtime(model_identifier: str | None) -> bool:
    profile = get_model_profile(model_identifier)
    return bool(profile and profile.requires_fla_runtime)


def model_needs_memory_optimization(model_identifier: str | None) -> bool:
    profile = get_model_profile(model_identifier)
    return bool(profile and profile.needs_memory_optimization)


def get_config_overrides(model_identifier: str | None) -> Mapping[str, Any] | None:
    """Return config.json overrides needed for a model family, or None if none needed."""
    profile = get_model_profile(model_identifier)
    return profile.config_overrides if profile else None


def get_tokenizer_kwargs(model_identifier: str | None) -> dict[str, Any]:
    """Return tokenizer kwargs needed for a model, or empty dict if none needed."""
    profile = get_model_profile(model_identifier)
    if profile and profile.tokenizer_kwargs:
        return dict(profile.tokenizer_kwargs)
    return {}


__all__ = [
    "AWQ_DEFAULT_DATASET",
    "AWQ_MODEL_MARKERS",
    "CHAT_TOTAL_POLICY",
    "TOOL_TOTAL_POLICY",
    "TOOLCALL_MODEL_MARKERS",
    "MODEL_PROFILES",
    "TotalLengthPolicy",
    "ModelProfile",
    "resolve_total_len",
    "canonicalize_dataset_name",
    "dataset_fallback",
    "dataset_key",
    "normalize_model_id",
    "is_toolcall_model",
    "get_model_profile",
    "model_requires_bfloat16",
    "model_requires_fla_runtime",
    "model_needs_memory_optimization",
    "get_config_overrides",
    "get_tokenizer_kwargs",
]

