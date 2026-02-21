"""Pytest collection rules for non-prefixed local test modules."""

from __future__ import annotations

import pytest
from pathlib import Path


def _is_collectable_test_module(path: Path) -> bool:
    if path.suffix != ".py" or path.name == "__init__.py":
        return False
    if "unit" in path.parts:
        return True
    return path.parent.name == "integration" and path.name == "sanitizer.py"


def pytest_collect_file(file_path: Path, parent):
    """Collect non-prefixed test modules under tests/unit and tests/integration/sanitizer.py."""
    if not _is_collectable_test_module(file_path):
        return None
    return pytest.Module.from_parent(parent, path=file_path)
