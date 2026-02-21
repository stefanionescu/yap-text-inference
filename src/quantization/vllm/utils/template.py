"""Template utilities for generating AWQ model documentation."""

import os
import json
from typing import Any
from textwrap import dedent
from src.hf.license import compute_license_info, resolve_template_name


def _parse_quant_summary(quant_summary: str) -> dict[str, Any]:
    try:
        return json.loads(quant_summary) if quant_summary.strip().startswith("{") else {}
    except json.JSONDecodeError:
        return {}


def _render_fallback(template_vars: dict[str, Any]) -> str:
    samples_line = template_vars.get("calibration_samples_line", "")
    return (
        dedent(
            f"""
        # {template_vars["model_name"]} — AWQ {template_vars["w_bit"]}-bit

        This model was quantized with [{template_vars["quantizer_name"]}]({template_vars["quantizer_link"]})
        from {template_vars["source_model_link"]}.

        - Quantizer version: `{template_vars["quantizer_version"]}`
        - Scheme: {template_vars["quant_scheme"]} | Targets: {template_vars["quant_targets"]}
        - Precision: group size {template_vars["q_group_size"]} | zero-point {template_vars["quant_zero_point"]}
        - Dataset: {template_vars["calibration_dataset_effective"]}
        {samples_line}- Max seq len: {template_vars["calibration_seq_len"]}

        ## {template_vars["quantizer_recipe_heading"]}
        ```json
        {template_vars["quant_summary"]}
        ```
        """
        ).strip()
        + "\n"
    )


def _format_list(value: Any) -> str:
    if isinstance(value, list | tuple | set):
        joined = ", ".join(str(v) for v in value if v)
        return joined or "none"
    if isinstance(value, str):
        value = value.strip()
        return value or "none"
    return "none"


def _format_zero_point(value: Any) -> str:
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    if isinstance(value, int | float):
        return "enabled" if value else "disabled"
    return "unspecified"


def _derive_quantizer_version(awq_version: str) -> str:
    if not awq_version:
        return "unknown"
    if "==" in awq_version:
        return awq_version.split("==", 1)[1]
    return awq_version


def _resolve_quantizer_fields(awq_version: str) -> dict[str, str]:
    version = _derive_quantizer_version(awq_version or "llmcompressor")

    return {
        "quantizer_name": "LLM Compressor",
        "quantizer_link": "https://github.com/vllm-project/llm-compressor",
        "quantizer_version": version,
        "quantizer_recipe_heading": "llmcompressor recipe",
    }


def _resolve_model_references(model_path: str) -> tuple[str, bool, str, str]:
    model_name = model_path.split("/")[-1] if "/" in model_path else model_path
    is_hf_model = "/" in model_path and not os.path.exists(model_path)
    source_model_link = f"[{model_path}](https://huggingface.co/{model_path})" if is_hf_model else f"`{model_path}`"
    base_model = model_path if is_hf_model else model_name
    return model_name, is_hf_model, source_model_link, base_model


def _resolve_quantization_fields(
    quant_summary: str,
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    quant_summary_data = _parse_quant_summary(quant_summary)
    quant_config = metadata.get("quantization_config") or quant_summary_data or {}
    quant_fields = {
        "w_bit": quant_config.get("w_bit", quant_summary_data.get("w_bit", 4)),
        "q_group_size": quant_config.get("q_group_size", quant_summary_data.get("q_group_size", "auto")),
        "quant_scheme": quant_config.get("scheme", quant_summary_data.get("scheme", "W4A16")),
        "quant_targets": _format_list(quant_config.get("targets", quant_summary_data.get("targets", "Linear"))),
        "quant_ignore": _format_list(quant_config.get("ignore", quant_summary_data.get("ignore", []))),
        "quant_zero_point": _format_zero_point(quant_config.get("zero_point", quant_summary_data.get("zero_point"))),
    }
    return quant_summary_data, {"quant_config": quant_config, **quant_fields}


def _resolve_calibration_fields(metadata: dict[str, Any], quant_config: dict[str, Any]) -> dict[str, Any]:
    dataset_info = metadata.get("calibration_dataset") or {}
    dataset_requested = dataset_info.get("requested") or dataset_info.get("effective") or "unknown"
    dataset_effective = dataset_info.get("effective") or dataset_requested
    dataset_fallback = dataset_info.get("fallback_from")
    if dataset_fallback:
        dataset_effective = f"{dataset_effective} (fallback from {dataset_fallback})"

    calib_config = metadata.get("calibration_config") or {}
    calibration_samples = calib_config.get("num_calibration_samples")
    calibration_seq_len = (
        calib_config.get("max_seq_length")
        or metadata.get("calibration_seqlen")
        or quant_config.get("max_seq_length")
        or "unknown"
    )
    calibration_samples_line = ""
    if calibration_samples is not None and str(calibration_samples) not in ("unknown", ""):
        calibration_samples_line = f"- Samples: {calibration_samples}\n"
    return {
        "calibration_dataset_effective": dataset_effective,
        "calibration_samples": calibration_samples,
        "calibration_samples_line": calibration_samples_line,
        "calibration_seq_len": calibration_seq_len,
    }


def _resolve_runtime_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    runtime_config = metadata.get("runtime_config") or {}
    runtime_engine = runtime_config.get("engine_name") or (
        "vLLM V1" if runtime_config.get("vllm_use_v1", True) else "vLLM V0 scheduler"
    )
    runtime_kv_dtype = runtime_config.get("kv_cache_dtype", "auto")
    runtime_kv_reuse = "enabled" if runtime_config.get("kv_cache_reuse", True) else "disabled"
    runtime_paged_attention = "enabled" if runtime_config.get("paged_attention", True) else "disabled"
    return {
        "runtime_engine": metadata.get("runtime_engine", runtime_engine),
        "runtime_kv_cache_dtype": metadata.get("runtime_kv_cache_dtype", runtime_kv_dtype),
        "runtime_kv_cache_reuse": metadata.get("runtime_kv_cache_reuse", runtime_kv_reuse),
        "runtime_paged_attention": metadata.get("runtime_paged_attention", runtime_paged_attention),
    }


def generate_readme(
    model_path: str,
    awq_version: str,
    quant_summary: str,
    metadata: dict[str, Any],
    out_dir: str,
) -> str:
    """Generate a comprehensive README using templates."""

    # Tool models are classification-only; AWQ exports are always chat models
    is_tool = False

    # Resolve template
    template_name = resolve_template_name(is_tool)
    template_path = os.path.join(os.path.dirname(__file__), "..", "readme", template_name)

    model_name, is_hf_model, source_model_link, base_model = _resolve_model_references(model_path)
    _, quant_fields = _resolve_quantization_fields(quant_summary, metadata)
    calibration_fields = _resolve_calibration_fields(metadata, quant_fields["quant_config"])

    awq_version = awq_version or metadata.get("awq_version") or "llmcompressor==unknown"
    quantizer_fields = _resolve_quantizer_fields(awq_version)
    hf_size_note = ""

    license_info = compute_license_info(model_path, is_tool=is_tool, is_hf_model=is_hf_model)
    runtime_fields = _resolve_runtime_fields(metadata)

    template_vars = {
        "model_name": model_name,
        "base_model": base_model,
        "source_model_link": source_model_link,
        "w_bit": quant_fields["w_bit"],
        "q_group_size": quant_fields["q_group_size"],
        "quant_scheme": quant_fields["quant_scheme"],
        "quant_targets": quant_fields["quant_targets"],
        "quant_ignore": quant_fields["quant_ignore"],
        "quant_zero_point": quant_fields["quant_zero_point"],
        "quant_summary": (quant_summary or "").strip() or "{}",
        "awq_version": awq_version,
        "calibration_dataset_effective": calibration_fields["calibration_dataset_effective"],
        "calibration_samples": calibration_fields["calibration_samples"],
        "calibration_samples_line": calibration_fields["calibration_samples_line"],
        "calibration_seq_len": calibration_fields["calibration_seq_len"],
        "hf_size_note": hf_size_note,
        **quantizer_fields,
        **license_info,
        **runtime_fields,
    }

    # Try to use template, fallback to basic if not found
    try:
        with open(template_path, encoding="utf-8") as f:
            template = f.read()
        return template.format(**template_vars)
    except FileNotFoundError:
        print(f"[awq] Warning: Template {template_name} not found, using basic README")
        return _render_fallback(template_vars)
