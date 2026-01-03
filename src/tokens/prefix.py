"""Screen prefix token counting and stripping utilities.

This module handles the screen prefix logic for chat sessions:

1. Token Counting:
   - Counts tokens for check_screen and screen_checked prefixes
   - Accounts for the space added when prefixing user messages
   - Used to adjust USER_UTT_MAX_TOKENS budget

2. Prefix Stripping:
   - Removes screen prefixes from user messages before storing in history
   - Handles both case-sensitive and case-insensitive matching
   - Prevents prefixes from polluting conversation history

3. Effective Budget Calculation:
   - Computes available tokens for user messages after prefix reservation
   - Supports both start messages (check_screen) and followups (screen_checked)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import (
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
    DEPLOY_CHAT,
    USER_UTT_MAX_TOKENS,
)
from .token_utils import count_tokens_chat

if TYPE_CHECKING:
    from ..handlers.session.state import SessionState


def count_prefix_tokens(prefix: str | None) -> int:
    """Count tokens for a prefix string (including trailing space).
    
    The trailing space is included because when we prefix a user message
    like "CHECK SCREEN: hello", we add a space after the prefix.
    
    Args:
        prefix: The prefix text to count tokens for.
        
    Returns:
        Token count including the trailing space, or 0 if prefix is empty
        or chat model is not deployed (prefixes only apply to chat).
    """
    if not prefix:
        return 0
    # Screen prefixes only apply when chat model is deployed
    if not DEPLOY_CHAT:
        return 0
    return count_tokens_chat(f"{prefix.strip()} ")


def strip_screen_prefix(
    text: str,
    check_screen_prefix: str | None,
    screen_checked_prefix: str | None,
) -> str:
    """Remove screen prefixes from text before storing in history.
    
    This prevents the internal "CHECK SCREEN:" or "ON THE SCREEN NOW:"
    prefixes from appearing in the conversation history that's shown
    to the model on subsequent turns.
    
    Handles both exact and case-insensitive matching to catch variations.
    
    Args:
        text: The user message text to strip prefixes from.
        check_screen_prefix: The check_screen prefix to strip (may be custom).
        screen_checked_prefix: The screen_checked prefix to strip (may be custom).
        
    Returns:
        The text with any matching prefix removed.
    """
    if not text:
        return ""

    def _try_strip(candidate: str | None, value: str) -> tuple[bool, str]:
        if not candidate:
            return False, value
        prefix_text = candidate.strip()
        if not prefix_text:
            return False, value
        prefix_len = len(candidate)
        # Exact match
        if value.startswith(candidate):
            return True, value[prefix_len:].lstrip()
        # Case-insensitive match
        lower_candidate = candidate.lower()
        if value.lower().startswith(lower_candidate):
            return True, value[prefix_len:].lstrip()
        return False, value

    # Collect unique prefixes to try
    prefixes: list[str] = []
    for candidate in (check_screen_prefix, screen_checked_prefix):
        if candidate and candidate not in prefixes:
            prefixes.append(candidate)

    # Try each prefix
    for prefix in prefixes:
        removed, updated = _try_strip(prefix, text)
        if removed:
            return updated

    return text


def get_effective_user_utt_max_tokens(
    state: SessionState | None,
    *,
    for_followup: bool = False,
) -> int:
    """Get the effective max tokens for user utterance after accounting for prefix.
    
    The user message budget is reduced by the tokens needed for the screen
    prefix, ensuring the total (prefix + message) fits within limits.
    
    Args:
        state: The session state containing cached prefix token counts.
            If None, uses default prefix token counts.
        for_followup: If True, account for screen_checked_prefix (followup messages).
            If False, account for check_screen_prefix (start messages).
            
    Returns:
        The adjusted max token count for user message content.
        Always returns at least 1 to prevent zero-length limits.
    """
    if state is None:
        # No session state: use defaults
        if for_followup:
            prefix_tokens = count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
        else:
            prefix_tokens = count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

    if for_followup:
        prefix_tokens = state.screen_checked_prefix_tokens
    else:
        prefix_tokens = state.check_screen_prefix_tokens

    return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)


__all__ = [
    "count_prefix_tokens",
    "strip_screen_prefix",
    "get_effective_user_utt_max_tokens",
]

