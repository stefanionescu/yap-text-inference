"""Shared typing for tool regression messages."""

from typing import TypeAlias

ToolDefaultEntry: TypeAlias = tuple[str, bool] | tuple[str, list[tuple[str, bool]]]

__all__ = ["ToolDefaultEntry"]
