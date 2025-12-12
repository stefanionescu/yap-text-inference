"""Personality switch phrase matching logic."""

import re
from functools import lru_cache

from ...config.patterns import PERSONALITY_SWITCH_TEMPLATES


def _build_personality_pattern(all_words: list[str]) -> str:
    """Build regex alternation pattern from personality words.
    
    Args:
        all_words: List of all personality names and synonyms
        
    Returns:
        Regex pattern like (friendly|flirty|savage|generic|horny)
    """
    # Escape any special regex characters in personality names
    escaped = [re.escape(word) for word in all_words]
    return "(" + "|".join(escaped) + ")"


@lru_cache(maxsize=128)
def _compile_patterns(personality_tuple: tuple[str, ...]) -> list[re.Pattern]:
    """Compile personality switch patterns for given personality words.
    
    Uses tuple for hashability with lru_cache.
    """
    personality_pattern = _build_personality_pattern(list(personality_tuple))
    compiled = []
    for template in PERSONALITY_SWITCH_TEMPLATES:
        pattern_str = template.format(personality_pattern)
        compiled.append(re.compile(pattern_str, re.IGNORECASE))
    return compiled


def _build_reverse_map(personalities: dict[str, list[str]]) -> dict[str, str]:
    """Build a reverse map from synonym/name -> canonical personality name.
    
    Args:
        personalities: Dict mapping personality name to list of synonyms
        
    Returns:
        Dict mapping any word (name or synonym) to canonical personality name
    """
    reverse_map: dict[str, str] = {}
    for personality_name, synonyms in personalities.items():
        name_lower = personality_name.lower()
        reverse_map[name_lower] = name_lower
        for synonym in synonyms:
            reverse_map[synonym.lower()] = name_lower
    return reverse_map


def match_personality_phrase(
    text: str,
    personalities: dict[str, list[str]] | None,
) -> str | None:
    """
    Check if text matches a personality switch pattern.
    
    Args:
        text: Stripped/normalized user utterance
        personalities: Dict mapping personality names to synonyms, or None
        
    Returns:
        The canonical personality name if matched, None otherwise
    """
    if not personalities:
        return None
    
    # Build list of all words (names + synonyms)
    all_words: list[str] = []
    for name, synonyms in personalities.items():
        all_words.append(name.lower())
        all_words.extend(s.lower() for s in synonyms)
    
    if not all_words:
        return None
    
    # Get compiled patterns (cached)
    patterns = _compile_patterns(tuple(sorted(all_words)))
    
    # Build reverse map for synonym resolution
    reverse_map = _build_reverse_map(personalities)
    
    # Check each pattern
    for pattern in patterns:
        match = pattern.match(text)
        if match:
            # Extract the captured personality word (group 1)
            matched_word = match.group(1).lower()
            # Resolve to canonical personality name
            return reverse_map.get(matched_word)
    
    return None
