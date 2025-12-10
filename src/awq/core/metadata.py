"""Persistence helpers for AWQ quantization outputs."""

from __future__ import annotations

import json
import os
from typing import Any

from ..utils.template_utils import generate_readme


def save_quantization_metadata(
    *,
    output_dir: str,
    model_path: str,
    awq_version: str,
    quant_config: dict[str, Any],
    target_seqlen: int,
    dataset_info: dict[str, str] | None = None,
    advanced_kwargs: dict[str, Any] | None = None,
) -> None:
    """Save metadata and generate README for a quantized model."""

    metadata: dict[str, Any] = {
        "source_model": model_path,
        "awq_version": awq_version,
        "quantization_config": quant_config,
        "calibration_seqlen": target_seqlen,
        "pipeline": "yap-text-inference",
    }

    if dataset_info:
        metadata["calibration_dataset"] = dataset_info

    if advanced_kwargs:
        metadata["calibration_config"] = advanced_kwargs

    meta_path = os.path.join(output_dir, "awq_metadata.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: failed to write metadata ({exc})")

    quant_summary = json.dumps(quant_config, indent=2)
    readme_contents = generate_readme(
        model_path=model_path,
        awq_version=awq_version,
        quant_summary=quant_summary,
        metadata=metadata,
        out_dir=output_dir,
    )

    readme_path = os.path.join(output_dir, "README.md")
    try:
        with open(readme_path, "w", encoding="utf-8") as file:
            file.write(readme_contents)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: failed to write README ({exc})")

    marker = os.path.join(output_dir, ".awq_ok")
    try:
        with open(marker, "w", encoding="utf-8") as file:
            file.write("ok")
    except Exception:
        pass
