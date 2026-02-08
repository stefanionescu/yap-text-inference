"""PyTorch/TorchVision CUDA version mismatch detection.

Detects when PyTorch and TorchVision were compiled against different CUDA
major versions, which causes RuntimeError on import. Shell scripts use this
to proactively uninstall mismatched packages before reinstalling.
"""

from __future__ import annotations

import sys
import importlib.util

# Exit code indicating CUDA mismatch was detected
EXIT_CODE_MISMATCH = 42


def detect_cuda_mismatch() -> tuple[bool, str]:
    """Detect PyTorch/TorchVision CUDA version mismatch.

    Returns:
        Tuple of (mismatch_detected, message).
        - mismatch_detected: True if packages have incompatible CUDA versions.
        - message: Error message with details, empty if no mismatch.
    """
    # Check if torch is installed
    torch_spec = importlib.util.find_spec("torch")
    if torch_spec is None:
        return False, ""

    import torch  # noqa: PLC0415

    # Check if torchvision is installed
    vision_spec = importlib.util.find_spec("torchvision")
    if vision_spec is None:
        return False, ""

    try:
        import torchvision  # noqa: F401, PLC0415
    except Exception as exc:
        message = str(exc).strip()
        needle = "PyTorch and torchvision were compiled with different CUDA major versions"
        if needle in message:
            # Build detailed message
            torch_ver = getattr(torch, "__version__", "")
            torch_cuda = (getattr(torch.version, "cuda", "") or "").strip()
            details = message
            if torch_ver:
                summary = f"torch=={torch_ver}"
                if torch_cuda:
                    summary += f" (CUDA {torch_cuda})"
                details = f"{message}\n{summary}"
            return True, details
        return False, ""

    return False, ""


if __name__ == "__main__":
    # CLI interface for shell scripts
    mismatch, message = detect_cuda_mismatch()

    if mismatch:
        if message:
            print(message)
        sys.exit(EXIT_CODE_MISMATCH)

    sys.exit(0)
