"""Voice configuration and parameter management."""

from server.config import settings


def resolve_voice(v: str) -> str:
    """
    Resolve voice parameter to internal voice name.
    Only accepts 'female' and 'male' as valid inputs.

    Args:
        v: Voice parameter string

    Returns:
        Internal voice name ("tara" or "zac")

    Raises:
        ValueError: If voice parameter is not 'female' or 'male'
    """
    if not v:
        raise ValueError("Voice is required and must be 'female' or 'male'.")

    key = v.strip().lower()

    # Only allow 'female' and 'male' as valid voice parameters
    if key not in settings.voice_aliases:
        raise ValueError(f"Invalid voice parameter '{v}'. Only 'female' and 'male' are supported.")

    return settings.voice_aliases[key]


def get_voice_defaults(voice: str) -> dict:
    """
    Get voice-specific default sampling parameters.

    Based on optimal settings:
    - Female (Tara): temperature=0.45, top_p=0.95, repetition_penalty=1.15
    - Male (Zac): temperature=0.45, top_p=0.95, repetition_penalty=1.15

    Args:
        voice: Voice parameter ('female' or 'male')

    Returns:
        Dict with default temperature, top_p, repetition_penalty for the voice
    """
    resolved = resolve_voice(voice)
    return settings.voice_defaults_by_internal.get(resolved, {})


def get_available_voices() -> list[str]:
    """Get list of available voice parameters."""
    return list(settings.voice_aliases.keys())


def get_voice_info() -> dict:
    """Get comprehensive voice configuration info."""
    return {
        "available_voices": get_available_voices(),
        "aliases": settings.voice_aliases,
        "defaults": {voice: get_voice_defaults(voice) for voice in get_available_voices()},
    }
