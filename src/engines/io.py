"""Shared IO helpers for inference engines."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

__all__ = ["read_json_file", "write_json_file"]

JsonValue = Any


def read_json_file(path: str | os.PathLike[str], *, encoding: str = "utf-8") -> JsonValue | None:
    """Best-effort JSON loader that returns None if the file is unreadable.
    
    Works with both str paths and Path objects.
    """
    # Handle Path objects
    if isinstance(path, Path) and not path.exists():
        return None
    
    try:
        with open(path, encoding=encoding) as fh:
            return json.load(fh)
    except Exception:
        return None


def write_json_file(
    path: str | os.PathLike[str],
    data: JsonValue,
    *,
    encoding: str = "utf-8",
) -> bool:
    """Best-effort JSON writer that atomically replaces the destination."""
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding=encoding) as fh:
            json.dump(data, fh, ensure_ascii=True, indent=2)
            fh.write("\n")
        os.replace(tmp_path, path)
        return True
    except Exception:
        with contextlib.suppress(Exception):
            os.remove(tmp_path)
        return False

