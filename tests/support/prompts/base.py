"""Base persona prompt templates.

These are the original flirty-only Anna/Mark prompts, now re-exported from
the detailed personality system for backwards compatibility.
"""

from .characters.mark import MARK_FLIRTY as MALE_PROMPT
from .characters.anna import ANNA_FLIRTY as FEMALE_PROMPT

__all__ = ["FEMALE_PROMPT", "MALE_PROMPT"]
