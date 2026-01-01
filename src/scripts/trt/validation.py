"""TRT installation and runtime validation helpers.

These functions validate that TRT-LLM dependencies are properly installed
and configured before engine building or inference.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import io
import sys


def validate_python_libraries() -> bool:
    """Validate that Python shared library is available and loadable.

    Returns:
        True if validation passes, False otherwise.
    """
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    lib_name = ctypes.util.find_library(f"python{version}")

    if not lib_name:
        print(
            "MISSING: Unable to locate libpython shared library. "
            "Install python3-dev and ensure LD_LIBRARY_PATH includes its directory.",
            file=sys.stderr,
        )
        return False

    try:
        ctypes.CDLL(lib_name)
    except OSError as exc:
        print(f"LOAD_ERROR: Found {lib_name} but failed to load it: {exc}", file=sys.stderr)
        return False

    print("[trt] ✓ Python shared library OK")
    return True


def validate_cuda_runtime() -> bool:
    """Validate CUDA Python bindings are installed and working.

    Returns:
        True if validation passes, False otherwise.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            ver = version("cuda-python")
        except PackageNotFoundError:
            print("MISSING: cuda-python not installed", file=sys.stderr)
            return False

        major = int(ver.split(".", 1)[0])
        try:
            if major >= 13:
                from cuda.bindings import runtime as cudart
            else:
                from cuda import cudart  # type: ignore[import-not-found,no-redef]
        except Exception as exc:
            print(f"IMPORT_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return False

        err, _ = cudart.cudaDriverGetVersion()
        if err != 0:
            print(f"CUDART_ERROR: cudaDriverGetVersion -> {err}", file=sys.stderr)
            return False

        print("[trt] ✓ CUDA runtime OK")
        return True

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def validate_mpi_runtime() -> bool:
    """Validate MPI runtime is available.

    Returns:
        True if validation passes, False otherwise.
    """
    try:
        from mpi4py import MPI

        MPI.Get_version()
        print("[trt] ✓ MPI runtime OK")
        return True
    except ImportError as exc:
        print(f"MISSING: mpi4py not installed: {exc}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"MPI_ERROR: {exc}", file=sys.stderr)
        return False


def validate_trt_installation() -> tuple[bool, str]:
    """Validate TensorRT-LLM installation and get version.

    Returns:
        Tuple of (success, version_or_error_message).
    """
    import logging
    import warnings

    try:
        # Suppress library's noisy output during import:
        # - stdout: version banner
        # - warnings: "Python 3.10 below recommended 3.11" UserWarning
        # - logging: various debug/info messages
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        logging.disable(logging.WARNING)
        warnings.filterwarnings("ignore", message=".*below the recommended.*")
        try:
            import tensorrt_llm

            version = tensorrt_llm.__version__
        finally:
            sys.stdout = old_stdout
            logging.disable(logging.NOTSET)

        print(f"[trt] ✓ TensorRT-LLM {version} installed")
        return True, version

    except ImportError as exc:
        # modelopt may be missing; this is a softer failure
        if "modelopt" in str(exc):
            return False, f"MODELOPT_MISSING: {exc}"
        return False, f"IMPORT_ERROR: {exc}"
    except Exception as exc:
        return False, f"ERROR: {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    # CLI interface for shell scripts
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.trt.validation <command>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "python-libs":
        sys.exit(0 if validate_python_libraries() else 1)

    elif cmd == "cuda-runtime":
        sys.exit(0 if validate_cuda_runtime() else 1)

    elif cmd == "mpi":
        sys.exit(0 if validate_mpi_runtime() else 1)

    elif cmd == "trt-install":
        success, result = validate_trt_installation()
        if success:
            print(result)
        else:
            print(result, file=sys.stderr)
        sys.exit(0 if success else 1)

    elif cmd == "all":
        # Run all validations
        all_ok = True
        all_ok = validate_python_libraries() and all_ok
        all_ok = validate_cuda_runtime() and all_ok
        success, _ = validate_trt_installation()
        all_ok = success and all_ok
        sys.exit(0 if all_ok else 1)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

