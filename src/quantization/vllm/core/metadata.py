"""Persistence helpers for AWQ quantization outputs."""

from __future__ import annotations

import os
import json
import contextlib
from typing import Any

from ..utils.template import generate_readme


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "off", "no"}


def _gather_runtime_metadata() -> dict[str, Any]:
    kv_dtype = os.getenv("KV_DTYPE", "auto")
    use_v1 = _env_flag("VLLM_USE_V1", True)
    paged_attention = _env_flag("VLLM_PAGED_ATTENTION", True)
    kv_reuse = _env_flag("VLLM_KV_CACHE_REUSE", bool(use_v1))
    return {
        "kv_cache_dtype": kv_dtype,
        "vllm_use_v1": use_v1,
        "paged_attention": paged_attention,
        "kv_cache_reuse": kv_reuse,
        "engine_name": "vLLM V1" if use_v1 else "vLLM V0 scheduler",
    }


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

    runtime_metadata = _gather_runtime_metadata()

    metadata: dict[str, Any] = {
        "source_model": model_path,
        "awq_version": awq_version,
        "quantization_config": quant_config,
        "calibration_seqlen": target_seqlen,
        "pipeline": "yap-text-inference",
        "runtime_config": runtime_metadata,
        "runtime_engine": runtime_metadata["engine_name"],
        "runtime_kv_cache_dtype": runtime_metadata["kv_cache_dtype"],
        "runtime_kv_cache_reuse": "enabled" if runtime_metadata["kv_cache_reuse"] else "disabled",
        "runtime_paged_attention": "enabled" if runtime_metadata["paged_attention"] else "disabled",
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
    with contextlib.suppress(Exception), open(marker, "w", encoding="utf-8") as file:
        file.write("ok")
