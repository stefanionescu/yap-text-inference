"""Tool-related dataclasses."""

from __future__ import annotations

from typing import Literal
from dataclasses import dataclass

_ScreenAction = Literal["no_screenshot", "take_screenshot", "pass"]


@dataclass(slots=True, frozen=True)
class FilterResult:
    """Result of the phrase filter."""

    action: _ScreenAction


__all__ = ["FilterResult", "_ScreenAction"]
