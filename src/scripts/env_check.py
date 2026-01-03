"""Environment check utilities for shell scripts.

Simple probes for checking package availability and versions.
Called from shell scripts to avoid inline Python heredocs.
"""

from __future__ import annotations

import sys


def get_torch_cuda_version() -> str | None:
    """Get the CUDA version that PyTorch was compiled with.

    Returns:
        CUDA version string (e.g., "13.0") or None if torch not available.
    """
    try:
        import torch

        cuda_ver = getattr(torch.version, "cuda", "") or ""
        return cuda_ver.strip() if cuda_ver.strip() else None
    except Exception:
        return None


def is_flashinfer_available() -> bool:
    """Check if FlashInfer is installed and importable.

    Returns:
        True if flashinfer can be imported, False otherwise.
    """
    try:
        import flashinfer  # noqa: F401

        return True
    except Exception:
        return False


if __name__ == "__main__":
    # CLI interface for shell scripts
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.env_check <command>", file=sys.stderr)
        print("Commands: torch-cuda-version, flashinfer-check", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "torch-cuda-version":
        result = get_torch_cuda_version()
        if result:
            print(result)
        sys.exit(0 if result else 1)

    elif cmd == "flashinfer-check":
        available = is_flashinfer_available()
        sys.exit(0 if available else 1)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

