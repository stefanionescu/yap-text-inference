"""HuggingFace integration utilities.

This package provides:
- Shared HF API wrappers (api.py)
- License computation for model cards (license.py)
- vLLM/AWQ model push workflows (vllm/)
- TRT-LLM model push workflows (trt/)
"""

from .api import get_hf_api, verify_repo_exists, create_repo_if_needed
from .license import compute_license_info, fetch_license_from_hf, resolve_template_name

__all__ = [
    "get_hf_api",
    "create_repo_if_needed",
    "verify_repo_exists",
    "resolve_template_name",
    "compute_license_info",
    "fetch_license_from_hf",
]

