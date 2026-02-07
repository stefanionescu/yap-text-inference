"""Lightweight screenshot phrase filter.

This module provides a fast regex-based filter for screenshot commands so the
classifier only runs when necessary. The filter recognizes two outcomes:

- take_screenshot: user explicitly requests a screenshot (including typo-safe
  variants and "check this out" style triggers)
- no_screenshot: explicit rejections such as "don't take a screenshot" or
  requests for multiple screenshots (which the server does not support)

If no pattern matches, the caller should fall back to the classifier model.
"""

from __future__ import annotations

import re

from src.state import FilterResult, _ScreenAction

from ...config.patterns import (
    SCREENSHOT_REJECT_PATTERNS,
    SCREENSHOT_TAKE_X_PATTERN,
    SCREENSHOT_TRIGGER_PATTERNS,
    SCREENSHOT_TRIGGER_QUANTITIES,
)

_SCREENSHOT_REJECT_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_REJECT_PATTERNS]
_SCREENSHOT_TAKE_X_COMPILED = re.compile(SCREENSHOT_TAKE_X_PATTERN, re.IGNORECASE)
_SCREENSHOT_TRIGGER_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_TRIGGER_PATTERNS]


def _match_screenshot(text: str) -> _ScreenAction:
    """Determine whether the utterance is an allow/deny screenshot command."""

    for pattern in _SCREENSHOT_REJECT_COMPILED:
        if pattern.match(text):
            return "no_screenshot"

    match = _SCREENSHOT_TAKE_X_COMPILED.match(text)
    if match:
        quantity = match.group(1).lower()
        if quantity in SCREENSHOT_TRIGGER_QUANTITIES:
            return "take_screenshot"
        return "no_screenshot"

    for pattern in _SCREENSHOT_TRIGGER_COMPILED:
        if pattern.match(text):
            return "take_screenshot"

    return "pass"


def filter_tool_phrase(user_utt: str) -> FilterResult:
    """Run the screenshot shortcut filter for a user utterance."""

    text = user_utt.strip()
    if not text:
        return FilterResult(action="pass")

    return FilterResult(action=_match_screenshot(text))


__all__ = ["filter_tool_phrase", "FilterResult"]
