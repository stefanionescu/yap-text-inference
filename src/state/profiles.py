"""Model profile dataclasses and profile catalog."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from collections.abc import Mapping


@dataclass(frozen=True)
class ModelProfile:
    """Describes special-case requirements for known model families."""

    name: str
    markers: tuple[str, ...]
    requires_bfloat16: bool = False
    requires_fla_runtime: bool = False
    uses_mla: bool = False
    needs_memory_optimization: bool = False
    max_num_batched_tokens: int | None = None
    config_overrides: Mapping[str, Any] | None = None
    tokenizer_kwargs: Mapping[str, Any] | None = None


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
    ModelProfile(
        name="deepseek-v2",
        markers=("deepseek-v2", "deepseek_v2", "deepseekcoder-v2", "deepseek-v3", "deepseek_v3"),
        uses_mla=True,
    ),
    ModelProfile(
        name="moonlight",
        markers=("moonlight",),
        requires_bfloat16=True,
        uses_mla=True,
    ),
    ModelProfile(
        name="qwen3-next",
        markers=("qwen3-next", "qwen3_next"),
        requires_bfloat16=True,
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
    ModelProfile(
        name="qwen3",
        markers=("qwen3",),
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
    ModelProfile(
        name="mistral-small-3",
        markers=("mistral-small-3",),
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
)


__all__ = [
    "ModelProfile",
    "MODEL_PROFILES",
]
