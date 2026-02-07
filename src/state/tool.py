"""Tool-related dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_ScreenAction = Literal["no_screenshot", "take_screenshot", "pass"]


@dataclass(slots=True, frozen=True)
class FilterResult:
    """Result of the phrase filter."""

    action: _ScreenAction


__all__ = ["FilterResult", "_ScreenAction"]
