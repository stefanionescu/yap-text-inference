"""Warmup script helpers.

Provides Python utilities used by the warmup shell script for persona
variant detection and configuration.
"""

from __future__ import annotations

import sys


def get_persona_variants() -> list[tuple[str, str]]:
    """Get persona variants from test configuration.

    Returns:
        List of (gender, personality) tuples.
    """
    try:
        from tests.config.defaults import PERSONA_VARIANTS

        result = []
        for gender, personality, _ in PERSONA_VARIANTS:
            if not gender:
                continue
            result.append((gender, personality or ""))
        return result
    except ImportError:
        return []


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

