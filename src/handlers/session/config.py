"""Session configuration update logic.

This module handles the mutable persona configuration for sessions:

1. Persona Fields:
   - chat_gender: Gender for the persona
   - chat_personality: Personality type (lowercased)
   - chat_prompt: Custom system prompt

2. Sampling Configuration:
   - chat_sampling: Custom sampling parameters dictionary

3. Screen Prefixes:
   - check_screen_prefix: Prefix for screenshot-triggering messages
   - screen_checked_prefix: Prefix for follow-up messages after screenshot

Each field is only updated if explicitly provided (not None), allowing
partial updates while preserving other configuration values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.config import DEFAULT_CHECK_SCREEN_PREFIX, DEFAULT_SCREEN_CHECKED_PREFIX

from ...tokens.prefix import count_prefix_tokens

if TYPE_CHECKING:
    from .state import SessionState


def update_session_config(
    state: SessionState,
    chat_gender: str | None = None,
    chat_personality: str | None = None,
    chat_prompt: str | None = None,
    chat_sampling: dict[str, Any] | None = None,
    check_screen_prefix: str | None = None,
    screen_checked_prefix: str | None = None,
) -> dict[str, Any]:
    """Update mutable persona configuration for a session.

    Only fields that are explicitly provided (not None) are updated.
    Other fields retain their current values.

    Args:
        state: The session state to update.
        chat_gender: New gender value, if provided.
        chat_personality: New personality (will be lowercased), if provided.
        chat_prompt: New custom system prompt, if provided.
        chat_sampling: New sampling parameters dict, if provided.
        check_screen_prefix: New check_screen prefix, if provided.
        screen_checked_prefix: New screen_checked prefix, if provided.

    Returns:
        Dict of field names to their new values (only changed fields).
    """
    meta = state.meta
    changed: dict[str, Any] = {}

    if chat_gender is not None:
        meta["chat_gender"] = chat_gender
        changed["chat_gender"] = chat_gender

    if chat_personality is not None:
        # chat_personality is already normalized/lowercased by validators
        meta["chat_personality"] = chat_personality or None
        changed["chat_personality"] = chat_personality or None

    if chat_prompt is not None:
        cp = chat_prompt or None
        meta["chat_prompt"] = cp
        changed["chat_prompt"] = bool(cp)

    if chat_sampling is not None:
        sampling = chat_sampling or None
        sampling_copy = sampling.copy() if isinstance(sampling, dict) else None
        meta["chat_sampling"] = sampling_copy
        changed["chat_sampling"] = sampling_copy.copy() if isinstance(sampling_copy, dict) else None

    if check_screen_prefix is not None:
        normalized = (check_screen_prefix or "").strip() or None
        meta["check_screen_prefix"] = normalized
        changed["check_screen_prefix"] = normalized
        # Recompute token count: use custom prefix or fall back to default
        effective_prefix = normalized or DEFAULT_CHECK_SCREEN_PREFIX
        state.check_screen_prefix_tokens = count_prefix_tokens(effective_prefix)

    if screen_checked_prefix is not None:
        normalized_checked = (screen_checked_prefix or "").strip() or None
        meta["screen_checked_prefix"] = normalized_checked
        changed["screen_checked_prefix"] = normalized_checked
        # Recompute token count: use custom prefix or fall back to default
        effective_prefix = normalized_checked or DEFAULT_SCREEN_CHECKED_PREFIX
        state.screen_checked_prefix_tokens = count_prefix_tokens(effective_prefix)

    return changed


def resolve_screen_prefix(
    state: SessionState | None,
    default: str,
    *,
    is_checked: bool = False,
) -> str:
    """Resolve the appropriate screen prefix for a session.

    Args:
        state: The session state, or None for defaults.
        default: The default prefix value to use.
        is_checked: If True, look for screen_checked_prefix.
            If False, look for check_screen_prefix.

    Returns:
        The resolved prefix string.
    """
    resolved_default = (default or "").strip()
    if not state:
        return resolved_default

    key = "screen_checked_prefix" if is_checked else "check_screen_prefix"
    prefix = (state.meta.get(key) or "").strip()
    return prefix or resolved_default


__all__ = ["update_session_config", "resolve_screen_prefix"]
