"""Reusable logic for uploading AWQ exports to HuggingFace."""

from __future__ import annotations

import os
import json
from typing import Any
from pathlib import Path

from src.config.quantization import AWQ_MODEL_MARKERS
from src.quantization.vllm.utils.template import generate_readme

_IGNORE_PATTERNS = [
    "*.tmp",
    "*.log",
    "__pycache__/*",
    "generation_config.json",
    "training_args.bin",
    "optimizer.pt",
    "scheduler.pt",
    "rng_state.pth",
]


def resolve_token(cli_token: str | None) -> str:
    """Resolve the HF token from CLI input or environment."""
    candidates = [
        cli_token,
        os.getenv("HF_TOKEN"),
        os.getenv("HUGGINGFACE_TOKEN"),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    raise SystemExit("[hf-push] HuggingFace token not provided. Set HF_AWQ_TOKEN or pass --token.")


def load_metadata(folder: Path) -> dict[str, Any]:
    meta_path = folder / "awq_metadata.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[hf-push] Warning: failed to read metadata ({exc})")
        return {}


def regenerate_readme(folder: Path, metadata: dict[str, Any]) -> None:
    source_model = (metadata.get("source_model") or "").strip() or "unknown"
    awq_version = metadata.get("awq_version") or "unknown"
    quant_config = metadata.get("quantization_config") or {}
    quant_summary = json.dumps(quant_config, indent=2)

    readme_contents = generate_readme(
        model_path=source_model,
        awq_version=awq_version,
        quant_summary=quant_summary,
        metadata=metadata,
        out_dir=str(folder),
    )

    readme_path = folder / "README.md"
    readme_path.write_text(readme_contents, encoding="utf-8")
    print("[hf-push] Regenerated README")


def classify_prequantized_source(value: str | None) -> str | None:
    if not value or "/" not in value:
        return None
    try:
        if Path(value).exists():
            return None
    except OSError:
        pass

    lowered = value.lower()
    if any(marker in lowered for marker in AWQ_MODEL_MARKERS):
        return "awq"
    if "gptq" in lowered:
        return "gptq"
    return None


__all__ = [
    "classify_prequantized_source",
    "load_metadata",
    "regenerate_readme",
    "resolve_token",
]
