"""Model profile lookup and query functions.

Provides functions to query model profiles and characteristics based on
model identifiers. Used across engines and quantization modules.
"""

from __future__ import annotations

from typing import Any

from src.config.model_profiles import MODEL_PROFILES, ModelProfile


def normalize_model_id(model_id: str | None) -> str:
    """Canonicalize model identifiers for substring comparisons."""
    return (model_id or "").strip().lower()


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


def model_uses_mla(model_identifier: str | None) -> bool:
    """Check if model uses MLA (Multi-Head Latent Attention), incompatible with FlashInfer."""
    profile = get_model_profile(model_identifier)
    return bool(profile and profile.uses_mla)


def get_tokenizer_kwargs(model_identifier: str | None) -> dict[str, Any]:
    """Return tokenizer kwargs needed for a model, or empty dict if none needed."""
    profile = get_model_profile(model_identifier)
    if profile and profile.tokenizer_kwargs:
        return dict(profile.tokenizer_kwargs)
    return {}


def get_max_batched_tokens(model_identifier: str | None) -> int | None:
    """Return the max_num_batched_tokens override for a model, or None if not set.
    
    Some models (e.g., Mistral Small 3.2) need higher batch sizes for acceptable
    TTFB. This function returns the profile-specific override if one exists.
    """
    profile = get_model_profile(model_identifier)
    if profile and profile.max_num_batched_tokens is not None:
        return profile.max_num_batched_tokens
    return None


__all__ = [
    "normalize_model_id",
    "get_model_profile",
    "model_requires_bfloat16",
    "model_requires_fla_runtime",
    "model_needs_memory_optimization",
    "model_uses_mla",
    "get_tokenizer_kwargs",
    "get_max_batched_tokens",
]

