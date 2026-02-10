"""Package availability validation.

Checks whether a Python package is importable. Designed to replace
inline ``python -c`` one-liners in shell scripts.

Usage:
    python -m src.scripts.validation.package importlinter   # exit 0 if installed
    python -m src.scripts.validation.package mypy           # exit 1 if missing
"""

from __future__ import annotations

import sys
import importlib.util

from src.config import PACKAGE_MIN_ARGS


def is_package_available(package_name: str) -> bool:
    """Check whether *package_name* can be imported.

    Args:
        package_name: Top-level package or module name (e.g. ``importlinter``).

    Returns:
        True if the package spec is found, False otherwise.
    """
    return importlib.util.find_spec(package_name) is not None


def main() -> int:
    """CLI entry point for shell script integration."""
    if len(sys.argv) < PACKAGE_MIN_ARGS:
        print("Usage: python -m src.scripts.validation.package <package>", file=sys.stderr)
        return 1

    return 0 if is_package_available(sys.argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main())
