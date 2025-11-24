"""Template utilities for generating AWQ model documentation.

Refactored to reduce indentation, remove magic values, and centralize
template/license selection in config.
"""

import json
import os
from textwrap import dedent
from typing import Any

from ..adapters.awq_toolcall_adapter import is_toolcall_model
from ...config.templates import resolve_template_name, compute_license_info


def _parse_quant_summary(quant_summary: str) -> dict[str, Any]:
    try:
        return json.loads(quant_summary) if quant_summary.strip().startswith('{') else {}
    except json.JSONDecodeError:
        return {}


def _render_fallback(model_path: str, awq_version: str, quant_summary: str, calib_section: str, repo_name: str) -> str:
    return dedent(f"""
    # AWQ Quantized Model

    - Source model: `{model_path}`
    - AWQ version: `{awq_version}`
    - Quantization config:
    ```json
    {quant_summary}
    ```

    ## Calibration
    {calib_section}

    ## Usage
    ```python
    from vllm import LLM
    
    engine = LLM(
        model="{repo_name}",
        quantization="awq",
        trust_remote_code=True,
    )
    ```
    """).strip() + "\n"


def generate_readme(
    model_path: str,
    awq_version: str,
    quant_summary: str,
    metadata: dict[str, Any],
    calib_section: str,
    out_dir: str
) -> str:
    """Generate a comprehensive README using templates."""

    # Determine if this is a tool model
    is_tool = is_toolcall_model(model_path)

    # Resolve template
    template_name = resolve_template_name(is_tool)
    template_path = os.path.join(os.path.dirname(__file__), "..", "readme", template_name)

    # Extract model name and details
    model_name = model_path.split('/')[-1] if '/' in model_path else model_path
    repo_name = os.path.basename(out_dir)

    # Create HuggingFace links if the source is a HF model
    is_hf_model = '/' in model_path and not os.path.exists(model_path)
    source_model_link = f"[{model_path}](https://huggingface.co/{model_path})" if is_hf_model else f"`{model_path}`"
    base_model = model_path if is_hf_model else ""

    # Get quantization details
    quant_config = _parse_quant_summary(quant_summary)
    w_bit = quant_config.get('w_bit', 4)
    q_group_size = quant_config.get('q_group_size', 128)

    # Generate model size estimates
    original_size_gb = metadata.get('original_size_gb', 'Unknown')
    quantized_size_gb = metadata.get('quantized_size_gb', 'Unknown')
    memory_reduction = 100 // w_bit if w_bit > 0 else 25

    # Original author for attribution
    original_author = model_path.split('/')[0] if '/' in model_path else 'the original authors'

    # License info from centralized config
    license_info = compute_license_info(model_path, is_tool=is_tool, is_hf_model=is_hf_model)

    # Template variables (only include what's actually used in the template)
    template_vars = {
        'model_name': model_name,
        'base_model': base_model,
        'source_model_link': source_model_link,
        'w_bit': w_bit,
        **license_info,
    }

    # Try to use template, fallback to basic if not found
    try:
        with open(template_path, encoding="utf-8") as f:
            template = f.read()
        return template.format(**template_vars)
    except FileNotFoundError:
        print(f"[awq] Warning: Template {template_name} not found, using basic README")
        return _render_fallback(model_path, awq_version, quant_summary, calib_section, repo_name)
