"""AWQ model metadata utilities.

Shell-callable helpers for reading AWQ metadata files and extracting
source model information from cached quantization artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def read_source_model(metadata_path: str) -> str | None:
    """Read the source model from an AWQ metadata file.

    Args:
        metadata_path: Path to awq_metadata.json file.

    Returns:
        Source model identifier, or None if not found.
    """
    path = Path(metadata_path)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = (data.get("source_model") or "").strip()
        return source if source else None
    except Exception:
        return None


if __name__ == "__main__":
    # CLI interface for shell scripts
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.awq <command> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "source-model" and len(sys.argv) >= 3:
        result = read_source_model(sys.argv[2])
        if result:
            print(result)
        sys.exit(0 if result else 1)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

