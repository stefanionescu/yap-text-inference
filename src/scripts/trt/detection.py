"""TRT checkpoint and environment detection helpers.

These functions are called from shell scripts to detect checkpoint quantization
formats, query CUDA driver versions, and list remote HuggingFace engines.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def detect_checkpoint_qformat(checkpoint_dir: str) -> str | None:
    """Detect quantization format from a TRT checkpoint config.

    Examines config.json in the checkpoint directory to determine the
    quantization algorithm used (fp8, int8_sq, int4_awq, etc.).

    Args:
        checkpoint_dir: Path to the checkpoint directory containing config.json.

    Returns:
        Detected qformat string (fp8, int8_sq, int4_awq) or None if not detected.
    """
    cfg_path = Path(checkpoint_dir) / "config.json"
    if not cfg_path.exists():
        return None

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Find quantization config under various possible keys
    quant: dict[str, Any] = {}
    for key in ("quantization_config", "quantization", "quant_config"):
        value = data.get(key)
        if isinstance(value, dict) and value:
            quant = value
            break

    if not quant:
        return None

    # Extract algorithm name
    algo = ""
    for key in ("quant_algo", "algorithm", "quantization_algo", "quantization_method"):
        raw_algo = quant.get(key)
        if isinstance(raw_algo, str):
            algo = raw_algo.lower()
            break

    # Extract weight bits
    w_bit = None
    for key in ("w_bit", "weight_bits", "weight_bit", "quant_bits"):
        raw = quant.get(key)
        if raw is not None:
            try:
                w_bit = int(raw) if isinstance(raw, str) else raw
            except (ValueError, TypeError):
                pass
            break

    # Determine qformat from algorithm string
    if "fp8" in algo:
        return "fp8"
    if "int8" in algo or "sq" in algo:
        return "int8_sq"
    if "int4" in algo or "awq" in algo:
        return "int4_awq"

    # Fall back to weight bits
    if isinstance(w_bit, int):
        if w_bit <= 4:
            return "int4_awq"
        if w_bit >= 8:
            return "fp8"

    return None


def get_cuda_driver_version() -> str | None:
    """Query the CUDA driver version using cuda-python bindings.

    Returns:
        Driver version string (e.g., "13.2") or None if unavailable.
    """
    try:
        try:
            from cuda.bindings import runtime as cudart
        except Exception:
            from cuda import cudart  # type: ignore[import-not-found,no-redef]

        err, ver = cudart.cudaDriverGetVersion()
        if err == 0:
            major = ver // 1000
            minor = (ver % 1000) // 10
            return f"{major}.{minor}"
    except Exception:
        pass
    return None


def list_remote_engines(repo_id: str) -> list[str]:
    """List available TRT engine directories from a HuggingFace repo.

    Args:
        repo_id: HuggingFace repository ID.

    Returns:
        List of engine labels (e.g., ["sm90_trt-llm-1.2.0rc5_cuda13.0"]).
    """
    try:
        from huggingface_hub import list_repo_tree

        items = list(
            list_repo_tree(repo_id, path_in_repo="trt-llm/engines", repo_type="model")
        )
        labels = []
        for item in items:
            if item.path.startswith("trt-llm/engines/") and item.path.count("/") == 2:
                label = item.path.split("/")[-1]
                labels.append(label)
        return labels
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return []


def read_checkpoint_quant_info(checkpoint_dir: str) -> dict[str, Any]:
    """Read quantization info from checkpoint config.json.

    Args:
        checkpoint_dir: Path to checkpoint directory.

    Returns:
        Quantization config dict, or empty dict if not found.
    """
    cfg_path = Path(checkpoint_dir) / "config.json"
    if not cfg_path.exists():
        return {}

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data.get("quantization", {})
    except Exception:
        return {}


if __name__ == "__main__":
    # CLI interface for shell scripts
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.trt.detection <command> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "qformat" and len(sys.argv) >= 3:
        result = detect_checkpoint_qformat(sys.argv[2])
        if result:
            print(result)
        sys.exit(0 if result else 1)

    elif cmd == "driver-version":
        result = get_cuda_driver_version()
        if result:
            print(result)
        sys.exit(0 if result else 1)

    elif cmd == "list-engines" and len(sys.argv) >= 3:
        from src.helpers.env import env_flag

        if not env_flag("SHOW_HF_LOGS", False):
            from src.scripts.filters import configure
            configure()
        engines = list_remote_engines(sys.argv[2])
        for engine in engines:
            print(engine)
        sys.exit(0)

    elif cmd == "quant-info" and len(sys.argv) >= 3:
        info = read_checkpoint_quant_info(sys.argv[2])
        print(json.dumps(info))
        sys.exit(0)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

