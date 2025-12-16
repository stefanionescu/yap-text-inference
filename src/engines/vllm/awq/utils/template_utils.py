"""Template utilities for generating AWQ model documentation.

Refactored to reduce indentation, remove magic values, and centralize
template/license selection in config.
"""

import json
import os
from textwrap import dedent
from typing import Any

from src.helpers.templates import resolve_template_name, compute_license_info


def _parse_quant_summary(quant_summary: str) -> dict[str, Any]:
    try:
        return json.loads(quant_summary) if quant_summary.strip().startswith('{') else {}
    except json.JSONDecodeError:
        return {}


def _render_fallback(template_vars: dict[str, Any]) -> str:
    samples_line = template_vars.get('calibration_samples_line', '')
    return (
        dedent(
            f"""
        # {template_vars['model_name']} — AWQ {template_vars['w_bit']}-bit

        This model was quantized with [{template_vars['quantizer_name']}]({template_vars['quantizer_link']})
        from {template_vars['source_model_link']}.

        - Quantizer version: `{template_vars['quantizer_version']}`
        - Scheme: {template_vars['quant_scheme']} | Targets: {template_vars['quant_targets']}
        - Precision: group size {template_vars['q_group_size']} | zero-point {template_vars['quant_zero_point']}
        - Dataset: {template_vars['calibration_dataset_effective']}
        {samples_line}- Max seq len: {template_vars['calibration_seq_len']}

        ## {template_vars['quantizer_recipe_heading']}
        ```json
        {template_vars['quant_summary']}
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
    raw = (awq_version or "").strip().lower()
    backend = raw.split("==", 1)[0] if raw else "llmcompressor"
    version = _derive_quantizer_version(awq_version or backend)

    if backend.startswith("autoawq"):
        return {
            "quantizer_name": "AutoAWQ",
            "quantizer_link": "https://github.com/casper-hansen/AutoAWQ",
            "quantizer_version": version,
            "quantizer_recipe_heading": "AutoAWQ config",
        }

    return {
        "quantizer_name": "LLM Compressor",
        "quantizer_link": "https://github.com/vllm-project/llm-compressor",
        "quantizer_version": version,
        "quantizer_recipe_heading": "llmcompressor recipe",
    }


def generate_readme(
    model_path: str,
    awq_version: str,
    quant_summary: str,
    metadata: dict[str, Any],
    out_dir: str,
) -> str:
    """Generate a comprehensive README using templates."""

    # Tool models are classifier-only now; AWQ exports are always chat models
    is_tool = False

    # Resolve template
    template_name = resolve_template_name(is_tool)
    template_path = os.path.join(os.path.dirname(__file__), "..", "readme", template_name)

    # Extract model name and details
    model_name = model_path.split('/')[-1] if '/' in model_path else model_path
    is_hf_model = '/' in model_path and not os.path.exists(model_path)
    source_model_link = f"[{model_path}](https://huggingface.co/{model_path})" if is_hf_model else f"`{model_path}`"
    base_model = model_path if is_hf_model else model_name

    quant_summary_data = _parse_quant_summary(quant_summary)
    quant_config = metadata.get("quantization_config") or quant_summary_data or {}
    w_bit = quant_config.get("w_bit", quant_summary_data.get("w_bit", 4))
    q_group_size = quant_config.get("q_group_size", quant_summary_data.get("q_group_size", "auto"))
    quant_scheme = quant_config.get("scheme", quant_summary_data.get("scheme", "W4A16"))
    quant_targets = _format_list(quant_config.get("targets", quant_summary_data.get("targets", "Linear")))
    quant_ignore = _format_list(quant_config.get("ignore", quant_summary_data.get("ignore", [])))
    quant_zero_point = _format_zero_point(quant_config.get("zero_point", quant_summary_data.get("zero_point")))

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
    # For samples, if unknown or not set, we'll omit the line entirely
    calibration_samples_line = ""
    if calibration_samples is not None and str(calibration_samples) not in ("unknown", ""):
        calibration_samples_line = f"- Samples: {calibration_samples}\n"

    awq_version = awq_version or metadata.get("awq_version") or "llmcompressor==unknown"
    quantizer_fields = _resolve_quantizer_fields(awq_version)
    hf_size_note = ""
    if quantizer_fields.get("quantizer_name") == "AutoAWQ":
        hf_size_note = (
            "\n> **Heads up:** Hugging Face currently recalculates the \"Model size\" badge "
            "only for repositories that declare the `compressed-tensors` format. "
            "AutoAWQ exports still use the classic AWQ tensor layout, so the dashboard may "
            "report the base model size even though the `.safetensors` files are quantized. "
            "Open the *Files* tab to see the true quantized sizes.\n"
        )

    license_info = compute_license_info(model_path, is_tool=is_tool, is_hf_model=is_hf_model)

    template_vars = {
        'model_name': model_name,
        'base_model': base_model,
        'source_model_link': source_model_link,
        'w_bit': w_bit,
        'q_group_size': q_group_size,
        'quant_scheme': quant_scheme,
        'quant_targets': quant_targets,
        'quant_ignore': quant_ignore,
        'quant_zero_point': quant_zero_point,
        'quant_summary': (quant_summary or "").strip() or "{}",
        'awq_version': awq_version,
        'calibration_dataset_effective': dataset_effective,
        'calibration_samples': calibration_samples,
        'calibration_samples_line': calibration_samples_line,
        'calibration_seq_len': calibration_seq_len,
        'hf_size_note': hf_size_note,
        **quantizer_fields,
        **license_info,
    }

    # Try to use template, fallback to basic if not found
    try:
        with open(template_path, encoding="utf-8") as f:
            template = f.read()
        return template.format(**template_vars)
    except FileNotFoundError:
        print(f"[awq] Warning: Template {template_name} not found, using basic README")
        return _render_fallback(template_vars)
