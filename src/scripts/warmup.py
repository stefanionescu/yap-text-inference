"""Warmup script helpers.

Provides Python utilities used by the warmup shell script for persona
variant detection and configuration.
"""

from __future__ import annotations

import sys
from src.config.personas import PERSONA_VARIANT_KEYS


def get_persona_variants() -> list[tuple[str, str]]:
    """Get shared persona variants used for warmup selection.

    Returns:
        List of (gender, personality) tuples.
    """
    result = []
    for gender, personality in PERSONA_VARIANT_KEYS:
        if not gender:
            continue
        result.append((gender, personality or ""))
    return result


def print_persona_variants() -> None:
    """Print persona variants in gender:personality format for shell consumption."""
    variants = get_persona_variants()
    for gender, personality in variants:
        print(f"{gender}:{personality}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_persona_variants()
    else:
        # Default behavior: print variants
        print_persona_variants()
