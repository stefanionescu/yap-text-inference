"""Prompt selection utilities for test utilities.

This module provides helpers for normalizing gender strings and selecting
appropriate chat prompts based on the assistant's gender and personality.

Prompt sources:
- tests/prompts/base.py: Basic prompts (Anna/Mark flirty only)
  Used by: warmup, bench, connections, screen_analysis, tool, history tests
  
- tests/prompts/detailed.py: Full personality matrix
  Used by: live client persona registry and scripts that accept --persona
"""

from __future__ import annotations

from tests.helpers.errors import PromptSelectionError
from tests.prompts.base import FEMALE_PROMPT, MALE_PROMPT
from tests.prompts.detailed import PERSONALITIES


def normalize_gender(value: str | None) -> str:
    """Normalize assistant gender strings to canonical lowercase tokens."""
    if not value:
        return ""
    return value.strip().lower()


def select_chat_prompt(gender: str | None) -> str:
    """
    Choose an appropriate chat prompt template based on assistant gender.
    
    Uses base prompts for the given gender.
    Defaults to the MALE_PROMPT (Mark) when the provided gender does not
    normalize to "female".
    
    Args:
        gender: "female" or "male"
        
    Returns:
        The full chat prompt string for the given gender with flirty personality.
        
    Raises:
        PromptSelectionError: If the resulting prompt is empty.
    """
    normalized = normalize_gender(gender)
    prompt = FEMALE_PROMPT if normalized == "female" else MALE_PROMPT

    print(prompt)
    
    if not prompt or not prompt.strip():
        raise PromptSelectionError(
            f"Selected prompt for gender '{gender}' is empty. "
            "Check that tests/prompts/base.py is correctly configured."
        )
    
    return prompt


def select_detailed_chat_prompt(gender: str | None, personality: str | None) -> str:
    """
    Select a chat prompt from the detailed personality matrix.
    
    This function looks up the full prompt from tests/prompts/detailed.py
    based on the combination of gender and personality.
    
    Args:
        gender: "female" or "male"
        personality: One of the available personalities (flirty, savage, religious, delulu, spiritual)
        
    Returns:
        The full chat prompt string for the given gender/personality combination.
        
    Raises:
        PromptSelectionError: If the combination is not found or prompt is empty.
    """
    normalized_gender = normalize_gender(gender)
    if not normalized_gender:
        raise PromptSelectionError("gender is required for detailed prompt selection")
    
    normalized_personality = (personality or "").strip().lower()
    if not normalized_personality:
        raise PromptSelectionError("personality is required for detailed prompt selection")
    
    # Build the lookup key (e.g., "anna_flirty" or "mark_savage")
    name = "anna" if normalized_gender == "female" else "mark"
    lookup_key = f"{name}_{normalized_personality}"
    
    persona_entry = PERSONALITIES.get(lookup_key)
    if persona_entry is None:
        available = ", ".join(sorted(PERSONALITIES.keys()))
        raise PromptSelectionError(
            f"No prompt found for '{lookup_key}'. "
            f"Available combinations: {available}"
        )
    
    prompt = persona_entry.get("prompt", "")
    if not prompt or not prompt.strip():
        raise PromptSelectionError(
            f"Prompt for '{lookup_key}' is empty. "
            "Check that tests/prompts/detailed.py is correctly configured."
        )
    
    return prompt


def get_persona_info(gender: str | None, personality: str | None) -> dict[str, str]:
    """
    Get full persona information including the prompt.
    
    Args:
        gender: "female" or "male"
        personality: One of the available personalities
        
    Returns:
        Dict with keys: gender, personality, prompt
        
    Raises:
        PromptSelectionError: If the combination is not found.
    """
    normalized_gender = normalize_gender(gender)
    if not normalized_gender:
        raise PromptSelectionError("gender is required for persona info")
    
    normalized_personality = (personality or "").strip().lower()
    if not normalized_personality:
        raise PromptSelectionError("personality is required for persona info")
    
    name = "anna" if normalized_gender == "female" else "mark"
    lookup_key = f"{name}_{normalized_personality}"
    
    persona_entry = PERSONALITIES.get(lookup_key)
    if persona_entry is None:
        available = ", ".join(sorted(PERSONALITIES.keys()))
        raise PromptSelectionError(
            f"No persona found for '{lookup_key}'. "
            f"Available combinations: {available}"
        )
    
    return {
        "gender": persona_entry["gender"],
        "personality": persona_entry["personality"],
        "prompt": persona_entry["prompt"],
    }


def validate_prompt_not_empty(prompt: str | None, context: str = "") -> str:
    """
    Validate that a prompt is not empty or whitespace-only.
    
    Args:
        prompt: The prompt string to validate.
        context: Optional context for error messages.
        
    Returns:
        The original prompt if valid.
        
    Raises:
        PromptSelectionError: If prompt is None, empty, or whitespace-only.
    """
    if prompt is None:
        ctx = f" ({context})" if context else ""
        raise PromptSelectionError(f"chat_prompt is required{ctx}")
    
    if not prompt.strip():
        ctx = f" ({context})" if context else ""
        raise PromptSelectionError(f"chat_prompt cannot be empty{ctx}")
    
    return prompt


__all__ = [
    "PromptSelectionError",
    "normalize_gender",
    "select_chat_prompt",
    "select_detailed_chat_prompt",
    "get_persona_info",
    "validate_prompt_not_empty",
]
