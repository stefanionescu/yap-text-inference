"""Python shared library validation.

Validates that the Python shared library (libpython) is present and loadable.
This is required for TensorRT-LLM and other native extensions.
"""

from __future__ import annotations

import sys
import ctypes
import ctypes.util


def get_python_version() -> str:
    """Get the current Python version as 'major.minor'."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def validate_python_library() -> tuple[bool, str]:
    """Validate that the Python shared library is loadable.

    Returns:
        Tuple of (success, message).
        If success is False, message contains the error description.
    """
    version = get_python_version()
    lib_name = ctypes.util.find_library(f"python{version}")

    if not lib_name:
        return False, (
            f"Unable to locate libpython{version} shared library. "
            "Install python3-dev and ensure LD_LIBRARY_PATH includes its directory."
        )

    try:
        ctypes.CDLL(lib_name)
    except OSError as exc:
        return False, f"Found {lib_name} but failed to load it: {exc}"

    return True, f"Python shared library OK: {lib_name}"


def main() -> int:
    """CLI entry point for shell script integration."""
    success, message = validate_python_library()
    if not success:
        print(f"[install] {message}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
