"""Lightweight IO helpers shared across subsystems."""

from __future__ import annotations

import json
import os
from typing import Any

JsonValue = Any


def read_json_file(path: str | os.PathLike[str], *, encoding: str = "utf-8") -> JsonValue | None:
    """Best-effort JSON loader that returns None if the file is unreadable."""
    try:
        with open(path, encoding=encoding) as fh:
            return json.load(fh)
    except Exception:
        return None


__all__ = ["read_json_file"]
