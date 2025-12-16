import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .utils import (
    render_template,
    safe_get,
    source_model_from_env_or_meta,
    template_repo_root,
    to_link,
)


def _build_quant_summary(  # noqa: PLR0913
    meta: dict,
    engine_label: str,
    trtllm_ver: str,
    awq_block_size: str,
    calib_size: str,
    dtype: str,
    max_input_len: str,
    max_output_len: str,
    max_batch_size: str,
) -> dict:
    return {
        "quantization": {
            "weights_precision": "int4_awq",
            "kv_cache_dtype": safe_get(meta, "quantization", "kv_cache", default="int8") or "int8",
            "awq_block_size": int(awq_block_size) if str(awq_block_size).isdigit() else awq_block_size,
            "calib_size": int(calib_size) if str(calib_size).isdigit() else calib_size,
        },
        "build": {
            "dtype": dtype,
            "max_input_len": int(max_input_len) if str(max_input_len).isdigit() else max_input_len,
            "max_output_len": int(max_output_len) if str(max_output_len).isdigit() else max_output_len,
            "max_batch_size": int(max_batch_size) if str(max_batch_size).isdigit() else max_batch_size,
            "engine_label": engine_label,
            "tensorrt_llm_version": trtllm_ver,
        },
        "environment": {
            "sm_arch": meta.get("sm_arch", ""),
            "gpu_name": meta.get("gpu_name", ""),
            "cuda_toolkit": meta.get("cuda_toolkit", ""),
            "nvidia_driver": meta.get("nvidia_driver", ""),
        },
    }


def _build_mapping(meta: dict, engine_label: str, repo_id: str) -> dict:
    base_model = source_model_from_env_or_meta(meta)
    awq_block_size = (
        os.environ.get("AWQ_BLOCK_SIZE")
        or str(safe_get(meta, "quantization", "awq_block_size", default="") or "")
        or "128"
    )
    calib_size = (
        os.environ.get("CALIB_SIZE") or str(safe_get(meta, "quantization", "calib_size", default="") or "") or "256"
    )
    dtype = os.environ.get("TRTLLM_DTYPE") or str(meta.get("dtype") or "float16")
    max_input_len = os.environ.get("TRTLLM_MAX_INPUT_LEN") or str(
        meta.get("max_input_len") or meta.get("max_input_len_tokens") or "48"
    )
    max_output_len = os.environ.get("TRTLLM_MAX_OUTPUT_LEN") or str(
        meta.get("max_output_len") or meta.get("max_output_len_tokens") or "1162"
    )
    max_batch_size = os.environ.get("TRTLLM_MAX_BATCH_SIZE") or str(meta.get("max_batch_size") or "16")
    trtllm_ver = meta.get("tensorrt_llm_version") or meta.get("tensorrt_version") or ""

    original_size_gb = str(safe_get(meta, "original_size_gb", default=6.0))
    quantized_size_gb = str(safe_get(meta, "quantized_size_gb", default=1.6))

    quant_summary = _build_quant_summary(
        meta,
        engine_label,
        trtllm_ver,
        awq_block_size,
        calib_size,
        dtype,
        max_input_len,
        max_output_len,
        max_batch_size,
    )

    mapping = {
        "license": "apache-2.0",
        "base_model": base_model,
        "model_name": "Orpheus 3B",
        "source_model_link": to_link(base_model),
        "w_bit": "4",
        "q_group_size": awq_block_size,
        "tensorrt_llm_version": trtllm_ver,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "original_size_gb": original_size_gb,
        "quantized_size_gb": quantized_size_gb,
        "quant_summary": json.dumps(quant_summary, ensure_ascii=False, indent=2),
        "calib_section": (
            f"- Method: Activation-aware weight quantization (AWQ)\n"
            f"- Calibration size: {calib_size}\n"
            f"- AWQ block/group size: {awq_block_size}\n"
            f"- DType for build: {dtype}\n"
        ),
        "engine_label": engine_label,
    }
    # Hardware/runtime specifics
    mapping["gpu_name"] = meta.get("gpu_name", "") or ""
    mapping["gpu_vram_gb"] = str(meta.get("gpu_vram_gb", "") or "")
    mapping["sm_arch"] = meta.get("sm_arch", "") or ""
    mapping["cuda_toolkit"] = meta.get("cuda_toolkit", "") or ""
    mapping["nvidia_driver"] = meta.get("nvidia_driver", "") or ""
    mapping["max_batch_size"] = max_batch_size
    mapping["repo_name"] = repo_id
    return mapping


def _fallback_lines(meta: dict, engine_label: str, what: str, repo_id: str) -> list[str]:  # noqa: PLR0915
    lines: list[str] = []
    lines.append("# TRT-LLM Artifacts\n")
    lines.append(
        "This repo contains TensorRT-LLM artifacts for Orpheus 3B (TTS). "
        "Engines are hardware/driver specific; checkpoints are portable."
    )
    lines.append("")
    lines.append("## Contents")
    lines.append("```")
    lines.append("trt-llm/")
    if what in ("engines", "both"):
        lines.append(f"  engines/{engine_label}/")
        lines.append("    rank*.engine")
        lines.append("    build_command.sh")
        lines.append("    build_metadata.json")
    if what in ("checkpoints", "both"):
        lines.append("  checkpoints/")
        lines.append("    rank*.safetensors")
        lines.append("    config.json")
    lines.append("```")

    lines.append("")
    lines.append("## Environment & Build Info")
    env_keys = [
        "tensorrt_llm_version",
        "tensorrt_version",
        "cuda_toolkit",
        "sm_arch",
        "gpu_name",
        "nvidia_driver",
        "platform",
        "build_image",
        "torch_version",
        "torch_cuda",
    ]
    env_lines = [f"- {k.replace('_', ' ').title()}: {meta[k]}" for k in env_keys if meta.get(k)]
    if env_lines:
        lines.extend(env_lines)

    build_knobs: list[str] = []
    for k in [
        "dtype",
        "max_batch_size",
        "max_input_len",
        "max_output_len",
    ]:
        v = meta.get(k)
        if v is not None and v != "":
            build_knobs.append(f"- {k.replace('_', ' ').title()}: {v}")
    q = meta.get("quantization", {})
    if q:
        build_knobs.append(
            "- Quantization: "
            f"weights={q.get('weights')}, kv_cache={q.get('kv_cache')}, "
            f"awq_block_size={q.get('awq_block_size')}, "
            f"calib_size={q.get('calib_size')}"
        )
    if build_knobs:
        lines.append("")
        lines.append("### Build knobs")
        lines.extend(build_knobs)

    build_cmd = meta.get("build_command", "")
    if build_cmd:
        lines.append("")
        lines.append("### Build command")
        lines.append("```")
        lines.append(build_cmd)
        lines.append("```")

    lines.append("")
    lines.append("## Portability Notes")
    lines.append(
        "- Engines (.engine/.plan) are NOT portable across GPU SM or TRT/CUDA versions. "
        "Use the exact environment above or rebuild from checkpoints."
    )
    lines.append("- Checkpoints (post-convert, pre-engine) are portable and recommended for sharing.")

    lines.append("")
    lines.append("## Download Examples (Python)")
    lines.append("```")
    lines.append("from huggingface_hub import snapshot_download")
    lines.append("# Download only engines for this arch")
    lines.append(f'path = snapshot_download(repo_id="{repo_id}", allow_patterns=["trt-llm/engines/{engine_label}/**"])')
    lines.append("")
    lines.append("# Or download checkpoints only")
    lines.append(f'path = snapshot_download(repo_id="{repo_id}", allow_patterns=["trt-llm/checkpoints/**"])')
    lines.append("```")
    return lines


def write_readme(repo_root: Path, engine_label: str, meta: dict, what: str, repo_id: str) -> None:
    template_path = template_repo_root() / "server" / "hf" / "orpheus-readme.md"
    mapping = _build_mapping(meta, engine_label, repo_id)

    if template_path.is_file():
        import contextlib

        with contextlib.suppress(Exception):
            template_text = template_path.read_text()
            rendered = render_template(template_text, mapping)
            (repo_root / "README.md").write_text(rendered)
            return

    lines = _fallback_lines(meta, engine_label, what, repo_id)
    (repo_root / "README.md").write_text("\n".join(lines))
