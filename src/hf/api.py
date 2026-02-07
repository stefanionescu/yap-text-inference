"""Lightweight wrappers around huggingface_hub for CLI tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - optional dependency
    from huggingface_hub import HfApi


def get_hf_api(token: str) -> HfApi | None:
    """Return an authenticated HfApi client, or None if unavailable."""
    try:
        from huggingface_hub import HfApi  # noqa: PLC0415
    except ImportError:
        print("[hf] Error: huggingface_hub not installed")
        return None
    return HfApi(token=token)


def create_repo_if_needed(
    api: HfApi,
    repo_id: str,
    token: str,
    private: bool,
) -> None:
    """Ensure a model repo exists (no-op on success)."""
    try:
        from huggingface_hub import create_repo  # noqa: PLC0415

        create_repo(repo_id, token=token, exist_ok=True, repo_type="model", private=private)
    except Exception as exc:  # noqa: BLE001
        print(f"[hf] Warning: Could not create repo {repo_id}: {exc}")


def verify_repo_exists(api: HfApi, repo_id: str, token: str) -> bool:
    """Return True if repo exists and is accessible to the token."""
    try:
        api.repo_info(repo_id=repo_id, token=token)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[hf] Error: Repository {repo_id} unavailable: {exc}")
        return False


__all__ = ["get_hf_api", "create_repo_if_needed", "verify_repo_exists"]
