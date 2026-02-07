#!/usr/bin/env python3
"""CLI entry point for pushing TRT-LLM artifacts to HuggingFace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.helpers.env import env_flag

if not env_flag("SHOW_HF_LOGS", False):
    from src.scripts.filters import configure

    configure()

from src.hf import get_hf_api, verify_repo_exists
from src.quantization.trt import get_engine_label
from src.state import TRTPushJob


def push_checkpoint_to_hf(
    checkpoint_dir: str,
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
    base_model: str | None = None,
    quant_method: str = "int4_awq",
    private: bool = False,
) -> bool:
    """Push TRT-LLM checkpoints and engines to HuggingFace."""
    api = get_hf_api(token)
    if api is None:
        return False

    checkpoint_path = Path(checkpoint_dir).expanduser()
    engine_path = Path(engine_dir).expanduser() if engine_dir else Path("__no_engine__")

    job = TRTPushJob(
        api=api,
        repo_id=repo_id,
        token=token,
        branch=branch,
        checkpoint_path=checkpoint_path,
        engine_path=engine_path,
        engine_provided=bool(engine_dir),
        base_model=base_model,
        quant_method=quant_method,
        private=private,
    )
    return job.run()


def push_engine_to_hf(
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
) -> bool:
    """Push only a TRT-LLM engine to an existing HuggingFace repository."""
    api = get_hf_api(token)
    if api is None:
        return False

    engine_path = Path(engine_dir)
    if not engine_path.is_dir():
        print(f"[trt-hf] Error: Engine directory not found: {engine_dir}")
    elif not list(engine_path.glob("rank*.engine")):
        print(f"[trt-hf] Error: No rank*.engine files found in {engine_dir}")
    else:
        try:
            engine_label = get_engine_label(engine_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[trt-hf] Error: Could not determine engine label: {exc}")
            return False

        if not verify_repo_exists(api, repo_id, token):
            return False

        engines_path = f"trt-llm/engines/{engine_label}"
        print("[trt-hf] Uploading engine...")

        try:
            api.upload_folder(
                folder_path=str(engine_path),
                path_in_repo=engines_path,
                repo_id=repo_id,
                token=token,
                revision=branch,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[trt-hf] Error: Failed to upload engine: {exc}")
            return False

        print(f"[trt-hf] ✓ Engine uploaded to {repo_id}")
        print(f"[trt-hf]   Path: {engines_path}")
        return True

    return False


# ============================================================================
# CLI
# ============================================================================


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-id", required=True, help="HuggingFace repo ID (owner/name)")
    parser.add_argument("--token", required=True, help="HuggingFace API token")
    parser.add_argument("--branch", default="main", help="Branch to push to")


def _add_full_push_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--checkpoint-dir", required=True, help="Path to TRT-LLM checkpoints")
    parser.add_argument("--engine-dir", default="", help="Path to TRT-LLM engines (optional)")
    parser.add_argument("--base-model", default="", help="Base model ID (auto-detected)")
    parser.add_argument("--quant-method", default="int4_awq", help="Quantization method")
    parser.add_argument("--private", action="store_true", help="Create private repo")


def _run_full_push(args: argparse.Namespace) -> int:
    success = push_checkpoint_to_hf(
        checkpoint_dir=args.checkpoint_dir,
        engine_dir=args.engine_dir or "",
        repo_id=args.repo_id,
        token=args.token,
        branch=args.branch,
        base_model=args.base_model or None,
        quant_method=args.quant_method,
        private=args.private,
    )
    return 0 if success else 1


def _run_engine_push(args: argparse.Namespace) -> int:
    success = push_engine_to_hf(
        engine_dir=args.engine_dir,
        repo_id=args.repo_id,
        token=args.token,
        branch=args.branch,
    )
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Push TRT-LLM model to HuggingFace")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    push_parser = subparsers.add_parser("push", help="Push checkpoint and engine")
    _add_common_args(push_parser)
    _add_full_push_args(push_parser)

    engine_parser = subparsers.add_parser("push-engine", help="Push only engine to existing repo")
    engine_parser.add_argument("--engine-dir", required=True, help="Path to TRT-LLM engines")
    _add_common_args(engine_parser)

    args = parser.parse_args()

    if args.command == "push":
        return _run_full_push(args)
    if args.command == "push-engine":
        return _run_engine_push(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

__all__ = ["push_checkpoint_to_hf", "push_engine_to_hf"]
