"""Test case construction and helpers for the tool regression suite.

This module provides functions to build test cases from the raw message data
in tests/messages/tool.py and helper functions for rendering conversation
history during multi-step test execution.
"""

from __future__ import annotations

from collections.abc import Sequence

from tests.messages.tool import TOOL_DEFAULT_MESSAGES
from tests.state import CaseStep, ToolTestCase

PAIR_LEN = 2


def _shorten(text: str, limit: int = 80) -> str:
    """Truncate text to a maximum length with ellipsis."""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def build_cases() -> list[ToolTestCase]:
    """
    Build test cases from TOOL_DEFAULT_MESSAGES.

    Supports two formats:
    - Simple: (message: str, expect_tool: bool)
    - Conversation: (name: str, [(message, expect_tool), ...])
    """
    cases: list[ToolTestCase] = []
    auto_counter = 0

    for idx, entry in enumerate(TOOL_DEFAULT_MESSAGES, start=1):
        if len(entry) == PAIR_LEN and isinstance(entry[0], str) and isinstance(entry[1], bool):
            auto_counter += 1
            message, expect_tool = entry
            case = ToolTestCase(
                uid=idx,
                name=f"single_{auto_counter:03d}",
                label=_shorten(message),
                steps=[CaseStep(text=message, expect_tool=expect_tool)],
            )
            cases.append(case)
            continue

        if len(entry) == PAIR_LEN and isinstance(entry[0], str) and isinstance(entry[1], list):
            name, messages = entry
            normalized_steps: list[CaseStep] = []
            for pair in messages:
                if not (isinstance(pair, tuple) and len(pair) == PAIR_LEN):
                    raise ValueError(f"Conversation '{name}' must contain (text, bool) tuples")
                text, expect = pair
                if not isinstance(text, str) or not isinstance(expect, bool):
                    raise ValueError(f"Conversation '{name}' entries must be (str, bool)")
                normalized_steps.append(CaseStep(text=text, expect_tool=expect))

            case = ToolTestCase(uid=idx, name=name, label=name, steps=tuple(normalized_steps))
            cases.append(case)
            continue

        raise ValueError(f"Unsupported test case entry: {entry!r}")

    return cases


def render_history(history: Sequence[CaseStep]) -> list[dict[str, str]]:
    """Render a sequence of case steps as conversation history."""
    if not history:
        return []
    messages: list[dict[str, str]] = []
    for step in history:
        messages.append({"role": "user", "content": step.text})
    return messages


__all__ = ["build_cases", "render_history"]
