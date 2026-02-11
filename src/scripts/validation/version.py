"""Package version lookup for shell script integration."""

from __future__ import annotations

import sys
from importlib import metadata

MIN_ARGS = 2


def get_package_version(package_name: str) -> str | None:
    """Return the package version or None if unavailable."""
    try:
        version = metadata.version(package_name)
    except Exception:
        return None
    if not version:
        return None
    return version


def main() -> int:
    """CLI entry point for version lookup.

    Usage:
        python -m src.scripts.validation.version <package>
    """
    if len(sys.argv) < MIN_ARGS:
        print("Usage: python -m src.scripts.validation.version <package>", file=sys.stderr)
        return 1

    package_name = sys.argv[1]
    version = get_package_version(package_name)
    if version:
        print(version)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["get_package_version", "main"]
