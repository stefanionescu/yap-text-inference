"""Regex assets shared by text sanitizers."""

from __future__ import annotations

import re

# Tool function names that should proceed to chat generation
# All other tool functions skip chat and return just the tool result
CHAT_CONTINUE_TOOLS: frozenset[str] = frozenset({"take_screenshot"})

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]",
    flags=re.UNICODE,
)

EMOTICON_PATTERN = re.compile(
    r"(?i)(?:"
    r"[:=;8][\-^]?[)dDpP(\]/\\oO]|"
    r":'\(|"
    r"<3|"
    r":-?\||"
    r":-?/|"
    r":3|"
    r";-?\)|"
    r"\^\_\^|"
    r"T_T|"
    r"¯\\_\(ツ\)_/¯"
    r")"
)

FREESTYLE_PREFIX_PATTERN = re.compile(r"^\s*(freestyle mode\.?)\s*", re.IGNORECASE)
ELLIPSIS_PATTERN = re.compile(r"…[ \t]*")
NEWLINE_TOKEN_PATTERN = re.compile(r"\s*(?:\\n|/n|\r?\n)+\s*")
FREESTYLE_TARGET_PREFIXES: tuple[str, ...] = ("freestyle mode", "freestyle mode.")
TRAILING_STREAM_UNSTABLE_CHARS = set(" \t\r\n/\\")
ESCAPED_QUOTE_PATTERN = re.compile(r'\\(["\'])')
DOUBLE_DOT_SPACE_PATTERN = re.compile(r"\.\.\s*")
EXAGGERATED_OH_PATTERN = re.compile(r"\b[oO][oOhH]+\b")
ELLIPSIS_TRAILING_DOT_PATTERN = re.compile(r"\.\.\.\s*\.")
LETTERS_ONLY_PATTERN = re.compile(r"^[A-Za-z]+$")

__all__ = [
    "CHAT_CONTINUE_TOOLS",
    "HTML_TAG_PATTERN",
    "EMOJI_PATTERN",
    "EMOTICON_PATTERN",
    "FREESTYLE_PREFIX_PATTERN",
    "ELLIPSIS_PATTERN",
    "NEWLINE_TOKEN_PATTERN",
    "FREESTYLE_TARGET_PREFIXES",
    "TRAILING_STREAM_UNSTABLE_CHARS",
    "ESCAPED_QUOTE_PATTERN",
    "DOUBLE_DOT_SPACE_PATTERN",
    "EXAGGERATED_OH_PATTERN",
    "ELLIPSIS_TRAILING_DOT_PATTERN",
    "LETTERS_ONLY_PATTERN",
]

