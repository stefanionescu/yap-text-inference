"""Model profile dataclasses."""

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


__all__ = ["ModelProfile"]
