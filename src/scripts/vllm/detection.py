"""vLLM and torch/CUDA detection helpers.

These functions detect torch and CUDA versions for FlashInfer wheel selection,
and check vLLM installation status.
"""

from __future__ import annotations

import sys


def get_cuda_version() -> str | None:
    """Get CUDA version from torch for FlashInfer wheel selection.

    Returns:
        CUDA version without dots (e.g., "126" for 12.6) or None.
    """
    try:
        import torch

        cu = (torch.version.cuda or "").strip()
        if not cu:
            return None
        return cu.replace(".", "")  # e.g., 12.6 -> 126
    except Exception:
        return None


def get_torch_version() -> str | None:
    """Get torch major.minor version for FlashInfer wheel selection.

    Returns:
        Torch version (e.g., "2.9") or None.
    """
    try:
        import torch

        ver = torch.__version__.split("+", 1)[0]
        parts = ver.split(".")
        return f"{parts[0]}.{parts[1]}"  # e.g., 2.9.0 -> 2.9
    except Exception:
        return None


def is_vllm_installed() -> bool:
    """Check if vLLM is installed.

    Returns:
        True if vLLM can be imported, False otherwise.
    """
    try:
        import vllm  # noqa: F401

        return True
    except ImportError:
        return False


def get_vllm_version() -> str:
    """Get vLLM version.

    Returns:
        vLLM version string or "unknown".
    """
    try:
        import vllm

        return vllm.__version__
    except Exception:
        return "unknown"


if __name__ == "__main__":
    # CLI interface for shell scripts
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.vllm.detection <command>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "cuda-version":
        result = get_cuda_version()
        if result:
            print(result)
            sys.exit(0)
        sys.exit(1)

    elif cmd == "torch-version":
        result = get_torch_version()
        if result:
            print(result)
            sys.exit(0)
        sys.exit(1)

    elif cmd == "is-installed":
        sys.exit(0 if is_vllm_installed() else 1)

    elif cmd == "version":
        print(get_vllm_version())
        sys.exit(0)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

