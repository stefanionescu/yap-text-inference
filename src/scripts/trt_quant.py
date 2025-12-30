"""
Utilities invoked by TRT quantization shell scripts.
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from typing import Iterable, Sequence


def _import_log_filter() -> None:
    """Import log filter to quiet noisy dependencies."""
    try:
        import src.scripts.log_filter  # noqa: F401
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


def _should_show_hf_progress() -> bool:
    """Check if HuggingFace progress bars should be shown."""
    val = os.environ.get("SHOW_HF_LOGS", "").lower()
    return val in ("1", "true", "yes")


def _enable_hf_progress() -> None:
    """Re-enable HuggingFace progress bars (undo log_filter suppression)."""
    # Remove env vars that disable progress
    os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
    os.environ.pop("TQDM_DISABLE", None)

    # Use HuggingFace API to enable progress bars
    try:
        from huggingface_hub.utils import enable_progress_bars

        enable_progress_bars()
    except Exception as e:
        print(f"[model] ⚠ Could not enable HF progress bars: {e}", file=sys.stderr)


def download_model(model_id: str, target_dir: str) -> None:
    """Download a Hugging Face model snapshot into target_dir."""
    import time

    from huggingface_hub import HfApi, snapshot_download

    # Check repo info first
    print("[model] Fetching repository metadata...", file=sys.stderr)
    start_time = time.time()

    # Enable progress bars BEFORE importing log_filter if user requested them
    show_progress = _should_show_hf_progress()
    if show_progress:
        _enable_hf_progress()
    else:
        _import_log_filter()

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

    from huggingface_hub import HfApi, snapshot_download

    print(f"[model] Repo: {model_id}", file=sys.stderr)
    print(f"[model] Target: {target_dir}", file=sys.stderr)

    # Check repo info first to give visibility into what we're downloading
    print("[model] Fetching repository metadata...", file=sys.stderr)
    try:
        api = HfApi()
        repo_info = api.repo_info(repo_id=model_id, repo_type="model")
        print(f"[model] ✓ Repository found: {repo_info.id}", file=sys.stderr)
        if repo_info.siblings:
            # Count relevant files
            patterns = ["trt-llm/checkpoints/", ".json", ".safetensors"]
            matching_files = [
                f
                for f in repo_info.siblings
                if any(p in f.rfilename for p in patterns)
            ]
            total_size = sum(f.size or 0 for f in matching_files if f.size)
            size_gb = total_size / (1024**3)
            print(
                f"[model] Files to download: {len(matching_files)} ({size_gb:.2f} GB)",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"[model] ⚠ Could not fetch repo info: {e}", file=sys.stderr)
        print("[model] Proceeding with download anyway...", file=sys.stderr)

    allow_patterns = ["trt-llm/checkpoints/**", "*.json", "*.safetensors"]
    start_time = time.time()

    # Enable progress bars if user requested them, otherwise apply log filter
    show_progress = _should_show_hf_progress()
    if show_progress:
        _enable_hf_progress()
    else:
        _import_log_filter()

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


def run_quantization(script_path: str, script_args: Iterable[str], patch_script: str | None) -> None:
    """Execute the quantization script with patches and noise suppression applied."""
    _apply_patch_script(patch_script or os.environ.get("TRANSFORMERS_PATCH_SCRIPT"))
    _import_log_filter()

    # Mirror the old -c wrapper behavior
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
        else:  # pragma: no cover - argparse enforces known commands
            raise ValueError(f"Unknown command: {args.command}")
    except Exception as exc:  # pragma: no cover - defensive guard for CLI
        print(f"[trt-quant] ✗ {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

