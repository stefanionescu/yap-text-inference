"""Regex assets shared by text sanitizers."""

from __future__ import annotations

import re

# Tool function names that should proceed to chat generation
# All other tool functions skip chat and return just the tool result
CHAT_CONTINUE_TOOLS: frozenset[str] = frozenset({"take_screenshot"})

# Hard-coded messages for control functions (switch_gender, switch_personality, etc.)
# These are cycled per session to ensure variety
CONTROL_FUNCTION_MESSAGES: tuple[str, ...] = (
    "All done",
    "Yup sure. Done.",
    "Alright, gimme a second. Done.",
    "Sure, it's done.",
    "That's done for ya.",
    "Sure thing, done.",
    "Consider it done.",
    "Right away. Done.",
    "There you go.",
    "No problem, done.",
    "Easy, done.",
    "You got it.",
    "Yep, all set.",
    "There ya go.",
    "Cool, all set.",
)

# Hard-coded messages for message rate limit responses
MESSAGE_RATE_LIMIT_MESSAGES: tuple[str, ...] = (
    "Wow you yap a lot, slow down a bit.",
    "I'm a bit overwhelmed sorry, give me a moment to recover.",
    "Damn you really talk a lot, give me a second to recover.",
    "My head's spinning, you're sending too many messages."
)

# Hard-coded messages for chat prompt update rate limit responses
CHAT_PROMPT_RATE_LIMIT_MESSAGES: tuple[str, ...] = (
    "I can't change moods that often, sorry.",
    "I'm not a robot, wait a bit before you change my personality.",
    "Nope sorry, you've changed my mood too many times.",
    "Don't wanna, I'll do it later."
)

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
    "CONTROL_FUNCTION_MESSAGES",
    "MESSAGE_RATE_LIMIT_MESSAGES",
    "CHAT_PROMPT_RATE_LIMIT_MESSAGES",
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

