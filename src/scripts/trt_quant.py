"""Utilities invoked by TRT quantization shell scripts."""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from typing import Sequence


def _apply_filters() -> None:
    """Apply log filters to quiet noisy dependencies."""
    try:
        import src.scripts.filters  # noqa: F401
    except Exception:
        # Logging noise suppression is best-effort; do not block work.
        pass


def _apply_patch_script(patch_script: str | None) -> None:
    """Execute the provided patch script, if present."""
    if not patch_script:
        return
    if not os.path.isfile(patch_script):
        print(f"[patch] Warning: patch script not found: {patch_script}", file=sys.stderr)
        return
    runpy.run_path(patch_script, run_name="__main__")


def _enable_hf_progress() -> None:
    """Re-enable HuggingFace progress bars (undo filter suppression)."""
    try:
        from src.scripts.filters.hf import enable_hf_progress
        enable_hf_progress()
        print("[model] ✓ HuggingFace progress bars enabled", file=sys.stderr)
    except Exception as e:
        print(f"[model] ⚠ Could not enable HF progress bars: {e}", file=sys.stderr)


def download_model(model_id: str, target_dir: str) -> None:
    """Download a Hugging Face model snapshot into target_dir."""
    import time

    from huggingface_hub import snapshot_download

    from src.helpers.env import env_flag

    print("[model] Fetching repository metadata...", file=sys.stderr)
    start_time = time.time()

    # Enable progress bars BEFORE applying filters if user requested them
    if env_flag("SHOW_HF_LOGS", False):
        _enable_hf_progress()
    else:
        _apply_filters()

    try:
        snapshot_download(repo_id=model_id, local_dir=target_dir)
    except KeyboardInterrupt:
        print("\n[model] ✗ Download interrupted by user", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[model] ✗ Download failed: {e}", file=sys.stderr)
        raise

    elapsed = time.time() - start_time
    print(f"[model] ✓ Download complete in {elapsed:.1f}s", file=sys.stderr)


def download_prequantized(model_id: str, target_dir: str) -> None:
    """Download pre-quantized TensorRT checkpoint assets."""
    import time

    from huggingface_hub import snapshot_download

    from src.helpers.env import env_flag

    print("[model] Fetching repository metadata...", file=sys.stderr)

    allow_patterns = ["trt-llm/checkpoints/**", "*.json", "*.safetensors"]
    start_time = time.time()

    # Enable progress bars if user requested them, otherwise apply filters
    if env_flag("SHOW_HF_LOGS", False):
        _enable_hf_progress()
    else:
        _apply_filters()

    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=target_dir,
            allow_patterns=allow_patterns,
        )
    except KeyboardInterrupt:
        print("\n[model] ✗ Download interrupted by user", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[model] ✗ Download failed: {e}", file=sys.stderr)
        raise

    elapsed = time.time() - start_time
    print(f"[model] ✓ Downloaded pre-quantized checkpoint in {elapsed:.1f}s", file=sys.stderr)


def run_quantization(
    script_path: str,
    script_args: list[str],
    patch_script: str | None,
) -> None:
    """Execute the quantization script with patches and noise suppression applied."""
    _apply_patch_script(patch_script or os.environ.get("TRANSFORMERS_PATCH_SCRIPT"))
    _apply_filters()

    print(file=sys.stderr)
    print("[quant] Starting quantization...", file=sys.stderr)

    sys.argv = [script_path, *script_args]
    runpy.run_path(script_path, run_name="__main__")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TRT quantization helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download-model", help="Download a Hugging Face model snapshot")
    dl.add_argument("--model-id", required=True)
    dl.add_argument("--target-dir", required=True)

    dl_pre = sub.add_parser("download-prequantized", help="Download pre-quantized TRT assets")
    dl_pre.add_argument("--model-id", required=True)
    dl_pre.add_argument("--target-dir", required=True)

    rq = sub.add_parser("run-quant", help="Run quantization script with patches applied")
    rq.add_argument("--patch-script", default=None, help="Path to transformers patch script")
    rq.add_argument("script", help="Path to quantization script to execute")
    rq.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments forwarded to the script")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        if args.command == "download-model":
            download_model(args.model_id, args.target_dir)
        elif args.command == "download-prequantized":
            download_prequantized(args.model_id, args.target_dir)
        elif args.command == "run-quant":
            run_quantization(args.script, args.script_args, args.patch_script)
        else:  # pragma: no cover
            raise ValueError(f"Unknown command: {args.command}")
    except Exception as exc:  # pragma: no cover
        print(f"[trt-quant] ✗ {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
