"""Shared IO helpers for inference engines."""

from __future__ import annotations

import os
import json
import logging
import contextlib
from typing import Any, TypeVar
from pathlib import Path

logger = logging.getLogger(__name__)

JsonValue = Any
PathLike = str | os.PathLike[str]
T = TypeVar("T")


def _coerce_path(path: PathLike) -> Path:
    """Coerce an input path into a Path object."""
    return path if isinstance(path, Path) else Path(path)


def read_json_file(
    path: PathLike,
    *,
    encoding: str = "utf-8",
    default: T | None = None,
) -> JsonValue | T | None:
    """Best-effort JSON loader.

    Args:
        path: File to read.
        encoding: File encoding.
        default: Value returned when the file is missing or invalid.
    """
    resolved = _coerce_path(path)
    if not resolved.exists():
        return default

    try:
        with resolved.open(encoding=encoding) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        logger.debug("Failed to decode JSON from %s: %s", resolved, exc)
    except OSError as exc:
        logger.debug("Failed to read %s: %s", resolved, exc)
    except Exception as exc:  # noqa: BLE001 - safeguard
        logger.debug("Unexpected error reading %s: %s", resolved, exc)
    return default


def write_json_file(
    path: PathLike,
    data: JsonValue,
    *,
    encoding: str = "utf-8",
    ensure_dir: bool = True,
) -> bool:
    """Best-effort JSON writer that atomically replaces the destination."""
    resolved = _coerce_path(path)
    tmp_path = resolved.with_suffix(resolved.suffix + ".tmp")

    if ensure_dir:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tmp_path.open("w", encoding=encoding) as fh:
            json.dump(data, fh, ensure_ascii=True, indent=2)
            fh.write("\n")
        os.replace(tmp_path, resolved)
        return True
    except Exception as exc:  # noqa: BLE001 - best effort writer
        logger.debug("Failed to write JSON to %s: %s", resolved, exc)
        with contextlib.suppress(Exception):
            os.remove(tmp_path)
        return False


__all__ = ["read_json_file", "write_json_file"]
