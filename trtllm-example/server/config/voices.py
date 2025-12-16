from dataclasses import dataclass, field


@dataclass(frozen=True)
class VoiceSettings:
    """Voice aliases and per-voice default sampling parameters."""

    # External → internal voice name mapping
    voice_aliases: dict[str, str] = field(
        default_factory=lambda: {
            "female": "tara",
            "male": "zac",
        }
    )

    # Per-internal-voice default sampling params
    voice_defaults_by_internal: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "tara": {
                "temperature": 0.45,
                "top_p": 0.95,
                "repetition_penalty": 1.15,
            },
            "zac": {
                "temperature": 0.45,
                "top_p": 0.95,
                "repetition_penalty": 1.15,
            },
        }
    )
