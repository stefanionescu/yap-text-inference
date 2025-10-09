"""Template utilities for generating AWQ model documentation."""

import json
import os
from textwrap import dedent
from typing import Dict, Any

from ..adapters.awq_hammer_adapter import is_hammer_model


def generate_readme(
    model_path: str,
    awq_version: str, 
    quant_summary: str,
    metadata: Dict[str, Any],
    calib_section: str,
    out_dir: str
) -> str:
    """Generate a comprehensive README using templates."""
    
    # Determine if this is a tool model
    is_tool = is_hammer_model(model_path)
    
    # Choose template based on model type
    template_name = "awq_tool_template.md" if is_tool else "awq_chat_template.md"
    template_path = os.path.join(os.path.dirname(__file__), "..", "readmes", template_name)
    
    # Extract model name and details
    model_name = model_path.split('/')[-1] if '/' in model_path else model_path
    repo_name = os.path.basename(out_dir)
    
    # Create HuggingFace links if the source is a HF model  
    is_hf_model = '/' in model_path and not os.path.exists(model_path)
    source_model_link = f"[{model_path}](https://huggingface.co/{model_path})" if is_hf_model else f"`{model_path}`"
    base_model = model_path if is_hf_model else ""
    
    # Get quantization details
    try:
        quant_config = json.loads(quant_summary) if quant_summary.strip().startswith('{') else {}
    except json.JSONDecodeError:
        quant_config = {}
    
    w_bit = quant_config.get('w_bit', 4)
    q_group_size = quant_config.get('q_group_size', 128)
    
    # Generate model size estimates
    original_size_gb = metadata.get('original_size_gb', 'Unknown')
    quantized_size_gb = metadata.get('quantized_size_gb', 'Unknown')
    memory_reduction = 100 // w_bit if w_bit > 0 else 25
    
    # Original author for attribution
    original_author = model_path.split('/')[0] if '/' in model_path else 'the original authors'
    
    # Determine license based on model type
    if is_tool:
        # Hammer models use Qwen research license
        license_info = {
            'license': 'other',
            'license_name': 'qwen-research', 
            'license_link': f'https://huggingface.co/{model_path}/blob/main/LICENSE' if is_hf_model else ''
        }
    else:
        # Chat models use Apache 2.0
        license_info = {
            'license': 'apache-2.0',
            'license_name': 'Apache 2.0',  # For consistency
            'license_link': ''  # Not needed for Apache
        }
    
    # Template variables
    template_vars = {
        'model_name': model_name,
        'repo_name': repo_name,
        'base_model': base_model,
        'source_model_link': source_model_link,
        'w_bit': w_bit,
        'q_group_size': q_group_size,
        'awq_version': awq_version,
        'generated_at': metadata.get('generated_at', 'Unknown'),
        'original_size_gb': original_size_gb,
        'quantized_size_gb': quantized_size_gb,
        'memory_reduction': memory_reduction,
        'calib_section': calib_section,
        'quant_summary': quant_summary,
        'original_author': original_author,
        **license_info,  # Add license info dynamically
    }
    
    # Try to use template, fallback to basic if not found
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.format(**template_vars)
    except FileNotFoundError:
        print(f"[awq] Warning: Template {template_name} not found, using basic README")
        # Inline fallback - no separate function needed
        return dedent(f"""
        # AWQ Quantized Model

        - Source model: `{model_path}`
        - AWQ version: `{awq_version}`
        - Quantization config:
        ```json
        {quant_summary}
        ```
        - Generated: {metadata.get('generated_at', 'Unknown')}

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
