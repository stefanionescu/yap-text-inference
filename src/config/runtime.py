"""Runtime environment configuration stub.

The actual configure_runtime_env() function has been moved to src/helpers/runtime.py.
This module re-exports it for backward compatibility.
"""

from __future__ import annotations

from src.helpers.runtime import configure_runtime_env

__all__ = ["configure_runtime_env"]
