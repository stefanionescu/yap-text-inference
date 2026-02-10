"""JSON metadata reader for shell script integration."""

from __future__ import annotations

import sys
import json
from typing import Any
from pathlib import Path

MIN_ARGS = 3


def read_metadata(metadata_path: str) -> dict[str, Any]:
    """Read JSON metadata from *metadata_path*.

    Args:
        metadata_path: Path to a JSON metadata file.

    Returns:
        Parsed JSON dict.
    """
    return json.loads(Path(metadata_path).read_text())


def get_metadata_field(metadata_path: str, key: str) -> str:
    """Get a string metadata field value, or empty string if missing."""
    try:
        data = read_metadata(metadata_path)
    except Exception:
        return ""
    value = data.get(key, "")
    if value is None:
        return ""
    return str(value)


def main() -> int:
    """CLI entry point for metadata field lookup.

    Usage:
        python -m src.scripts.validation.metadata <metadata_path> <key>
    """
    if len(sys.argv) < MIN_ARGS:
        print("Usage: python -m src.scripts.validation.metadata <metadata_path> <key>", file=sys.stderr)
        return 1

    metadata_path = sys.argv[1]
    key = sys.argv[2]
    value = get_metadata_field(metadata_path, key)
    if value:
        print(value)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["get_metadata_field", "read_metadata", "main"]
