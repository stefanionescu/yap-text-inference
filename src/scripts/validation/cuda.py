"""CUDA runtime validation.

Validates CUDA Python bindings are installed and functional.
Also provides utilities to query the CUDA driver version.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version as pkg_version

CUDA13_MAJOR = 13


def get_cuda_driver_version() -> tuple[bool, str]:
    """Get the CUDA driver version via cuda-python bindings.

    Returns:
        Tuple of (success, version_string).
        If success is False, version_string contains the error message.
        If success is True, version_string is like "13.2".
    """
    try:
        try:
            ver = pkg_version("cuda-python")
        except PackageNotFoundError:
            return False, "cuda-python not installed"

        major = int(ver.split(".", 1)[0])
        try:
            if major >= CUDA13_MAJOR:
                from cuda.bindings import runtime as cudart  # noqa: PLC0415
            else:
                from cuda import cudart  # noqa: PLC0415
        except Exception as exc:
            return False, f"Import error: {type(exc).__name__}: {exc}"

        err, driver_ver = cudart.cudaDriverGetVersion()
        if err != 0:
            return False, f"cudaDriverGetVersion error: {err}"

        # driver_ver is e.g. 13020 for CUDA 13.2
        cuda_major = driver_ver // 1000
        cuda_minor = (driver_ver % 1000) // 10
        return True, f"{cuda_major}.{cuda_minor}"

    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"


def validate_cuda_runtime() -> tuple[bool, str]:
    """Validate CUDA Python bindings are functional.

    Returns:
        Tuple of (success, message).
    """
    try:
        try:
            ver = pkg_version("cuda-python")
        except PackageNotFoundError:
            return False, "MISSING: cuda-python not installed"

        major = int(ver.split(".", 1)[0])
        try:
            if major >= CUDA13_MAJOR:
                from cuda.bindings import runtime as cudart  # noqa: PLC0415
            else:
                from cuda import cudart  # noqa: PLC0415
        except Exception as exc:
            return False, f"IMPORT_ERROR: {type(exc).__name__}: {exc}"

        err, _ = cudart.cudaDriverGetVersion()
        if err != 0:
            return False, f"CUDART_ERROR: cudaDriverGetVersion -> {err}"

        return True, "CUDA runtime OK"

    except Exception as exc:
        return False, f"ERROR: {type(exc).__name__}: {exc}"


def main() -> int:
    """CLI entry point for shell script integration.

    Usage:
        python -m src.scripts.validation.cuda           # Validate CUDA runtime
        python -m src.scripts.validation.cuda --driver  # Get driver version only
    """
    # Check for --driver flag to just output version
    if len(sys.argv) > 1 and sys.argv[1] in ("--driver", "--driver-version"):
        success, version_or_error = get_cuda_driver_version()
        if success:
            print(version_or_error)
            return 0
        else:
            # Print empty for shell compatibility (error to stderr)
            print("", file=sys.stdout)
            return 1

    # Default: validate CUDA runtime
    success, message = validate_cuda_runtime()
    if not success:
        print(f"[install] {message}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
