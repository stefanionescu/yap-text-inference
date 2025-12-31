#!/usr/bin/env python3
"""CLI entry point for uploading AWQ exports to HuggingFace."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.helpers.env import env_flag

if not env_flag("SHOW_HF_LOGS", False):
    import src.scripts.filters  # noqa: F401 - suppress HF progress bars

from src.hf import get_hf_api
from .push_job import AWQPushJob, resolve_token

__all__ = ["push_awq_to_hf"]


def push_awq_to_hf(
    src: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
    commit_message: str | None = None,
    private: bool = False,
    allow_create: bool = True,
) -> bool:
    """Push a local AWQ directory to HuggingFace."""
    src_dir = Path(src).resolve()
    if not src_dir.is_dir():
        print(f"[hf-push] AWQ folder not found: {src_dir}")
        return False

    api = get_hf_api(token)
    if api is None:
        return False

    job = AWQPushJob(
        api=api,
        repo_id=repo_id,
        token=token,
        branch=branch,
        commit_message=commit_message or f"Upload AWQ weights for {src_dir.name}",
        src_dir=src_dir,
        private=private,
        allow_create=allow_create,
    )
    return job.run()


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Push an AWQ directory to Hugging Face Hub")
    parser.add_argument("--src", required=True, help="Local AWQ folder to upload")
    parser.add_argument("--repo-id", required=True, help="Target repository, e.g. org/model-awq")
    parser.add_argument("--token", help="Hugging Face token (falls back to env)")
    parser.add_argument("--branch", default="main", help="Repository branch to push to")
    parser.add_argument("--commit-message", default=None, help="Custom commit message")
    parser.add_argument("--private", action="store_true", help="Create the repo as private if missing")
    parser.add_argument(
        "--no-create",
        action="store_false",
        dest="allow_create",
        default=True,
        help="Disable automatic repo creation",
    )

    args = parser.parse_args()

    repo_id = args.repo_id.strip()
    if not repo_id:
        raise SystemExit("[hf-push] Repository id cannot be empty")
    if repo_id.startswith("your-org/"):
        raise SystemExit("[hf-push] Please set --repo-id to your actual Hugging Face repo.")

    token = resolve_token(args.token)
    success = push_awq_to_hf(
        src=args.src,
        repo_id=repo_id,
        token=token,
        branch=args.branch,
        commit_message=args.commit_message,
        private=args.private,
        allow_create=args.allow_create,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
