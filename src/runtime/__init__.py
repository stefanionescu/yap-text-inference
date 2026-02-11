"""Runtime dependency wiring for eager startup initialization."""

from .dependencies import RuntimeDeps
from .bootstrap import build_runtime_deps

__all__ = [
    "build_runtime_deps",
    "RuntimeDeps",
]
