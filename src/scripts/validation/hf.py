"""HuggingFace authentication validation.

Validates that the HF_TOKEN environment variable is set and valid.
"""

from __future__ import annotations

import os
import sys
import warnings


def validate_hf_auth(token: str | None = None) -> tuple[bool, str]:
    """Validate HuggingFace authentication.

    Args:
        token: HF token to validate. If None, reads from HF_TOKEN env var.

    Returns:
        Tuple of (success, message).
    """
    if token is None:
        token = os.environ.get("HF_TOKEN")

    if not token:
        return False, "HF_TOKEN not set"

    try:
        from huggingface_hub import login  # noqa: PLC0415

        login(token=token, add_to_git_credential=False)
        return True, "HuggingFace authentication OK"
    except Exception as exc:
        return False, f"HuggingFace login failed: {type(exc).__name__}: {exc}"


def main() -> int:
    """CLI entry point for shell script integration."""
    # Suppress HF_TOKEN warning from huggingface_hub
    warnings.filterwarnings("ignore", message=r".*Environment variable.*HF_TOKEN.*is set.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
    success, message = validate_hf_auth()
    if not success:
        print(f"[install] {message}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
