"""Repository path setup for test scripts.

This module provides a helper to ensure the repository root is on sys.path,
allowing test scripts to import from the tests package regardless of how
they are invoked (directly, via pytest, or from subdirectories).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def setup_repo_path() -> str:
    """Ensure the repository root is on sys.path and return it."""
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    # Some scripts still expect os.getcwd() to be the repo root; ensure it exists.
    os.environ.setdefault("YAP_REPO_ROOT", repo_root_str)
    return repo_root_str


__all__ = ["setup_repo_path"]
