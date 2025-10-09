#!/usr/bin/env python3
"""Utility to push AWQ quantized model folders to Hugging Face Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from huggingface_hub import HfApi
except Exception as exc:  # pragma: no cover - import error path
    print(f"[hf-push] huggingface_hub is required: {exc}", file=sys.stderr)
    sys.exit(1)


def _load_metadata(folder: Path) -> Dict[str, Any]:
    meta_path = folder / "awq_metadata.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - metadata optional
        print(f"[hf-push] Warning: failed to read metadata ({exc})", file=sys.stderr)
        return {}


def _resolve_token(cli_token: Optional[str]) -> str:
    candidates = [
        cli_token,
        os.getenv("HF_TOKEN"),
        os.getenv("HUGGINGFACE_TOKEN"),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    raise SystemExit("[hf-push] Hugging Face token not provided. Set HF_AWQ_TOKEN or pass --token.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push an AWQ directory to Hugging Face Hub")
    parser.add_argument("--src", required=True, help="Local AWQ folder to upload")
    parser.add_argument("--repo-id", required=True, help="Target repository, e.g. org/model-awq")
    parser.add_argument("--token", help="Hugging Face token (falls back to HF_AWQ_TOKEN/HF_TOKEN env)")
    parser.add_argument("--branch", default="main", help="Repository branch to push to (default: main)")
    parser.add_argument("--commit-message", default=None, help="Custom commit message")
    parser.add_argument("--private", action="store_true", help="Create the repo as private if it does not exist")
    parser.add_argument("--no-create", action="store_false", dest="allow_create", default=True, help="Disable repo creation")

    args = parser.parse_args()

    src_dir = Path(args.src).resolve()
    if not src_dir.is_dir():
        raise SystemExit(f"[hf-push] AWQ folder not found: {src_dir}")

    repo_id = args.repo_id.strip()
    if not repo_id:
        raise SystemExit("[hf-push] Repository id cannot be empty")
    if repo_id.startswith("your-org/"):
        raise SystemExit("[hf-push] Please set --repo-id to your actual Hugging Face repo.")

    token = _resolve_token(args.token)

    metadata = _load_metadata(src_dir)
    source_model = metadata.get("source_model") or "unknown"

    commit_message = args.commit_message or f"Upload AWQ weights for {source_model}"

    api = HfApi(token=token)
    if args.allow_create:
        api.create_repo(repo_id=repo_id, private=args.private, exist_ok=True)

    print(f"[hf-push] Uploading {src_dir} -> {repo_id}@{args.branch}")
    api.upload_folder(
        folder_path=str(src_dir),
        repo_id=repo_id,
        repo_type="model",
        revision=args.branch,
        commit_message=commit_message,
        token=token,
        ignore_patterns=["*.tmp", "*.log", "__pycache__/*"],
    )
    print("[hf-push] Upload complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
