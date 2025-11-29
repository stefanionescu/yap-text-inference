from __future__ import annotations

import os
import sys
from pathlib import Path


def setup_repo_path() -> str:
    """Ensure the repository root is on sys.path and return it."""
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    # Some scripts still expect os.getcwd() to be the repo root; ensure it exists.
    os.environ.setdefault("YAP_REPO_ROOT", repo_root_str)
    return repo_root_str


__all__ = ["setup_repo_path"]
