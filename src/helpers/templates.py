"""Template and license computation helpers for AWQ README generation."""

from __future__ import annotations

from src.config.templates import (
    CHAT_TEMPLATE_NAME,
    MISTRAL_RESEARCH_MODELS,
    MISTRAL_RESEARCH_LICENSE,
    QWEN_LICENSE_MODELS,
    QWEN_LICENSE,
)


def resolve_template_name(is_tool: bool) -> str:
    return CHAT_TEMPLATE_NAME


def _is_mistral_research_model(model_path: str) -> bool:
    normalized = (model_path or "").strip()
    if not normalized:
        return False
    for target in MISTRAL_RESEARCH_MODELS:
        if normalized == target or normalized.endswith(target):
            return True
    return False


def _license_link_for(model_path: str, is_hf_model: bool) -> str:
    if not is_hf_model:
        return "LICENSE"
    return f"https://huggingface.co/{model_path}/blob/main/LICENSE"


def _is_qwen_license_model(model_path: str) -> bool:
    normalized = (model_path or "").strip()
    if not normalized:
        return False
    for target in QWEN_LICENSE_MODELS:
        if normalized == target or normalized.endswith(target):
            return True
    return False


def fetch_license_from_hf(model_id: str) -> dict[str, str] | None:
    """Fetch license information from a HuggingFace model repository.
    
    Args:
        model_id: HuggingFace model ID (e.g., "meta-llama/Llama-3.1-8B-Instruct").
        
    Returns:
        Dictionary with license, license_name, license_link keys, or None if fetch fails.
    """
    if not model_id or "/" not in model_id:
        return None
    
    try:
        from huggingface_hub import model_info
    except ImportError:
        print("[license] Warning: huggingface_hub not installed, cannot fetch license")
        return None
    
    try:
        info = model_info(model_id)
        card_data = info.card_data
        
        if not card_data:
            return None
        
        license_val = getattr(card_data, "license", None)
        if not license_val:
            return None
        
        # license_name and license_link may be specified in the model card
        license_name = getattr(card_data, "license_name", None) or license_val
        license_link = getattr(card_data, "license_link", None)
        
        # If no explicit link, try to construct one for the base model
        if not license_link:
            license_link = f"https://huggingface.co/{model_id}/blob/main/LICENSE"
        
        return {
            "license": license_val,
            "license_name": license_name,
            "license_link": license_link,
        }
    except Exception as e:
        print(f"[license] Warning: Could not fetch license from {model_id}: {e}")
        return None


def compute_license_info(model_path: str, is_tool: bool, is_hf_model: bool) -> dict[str, str]:
    """Return license info dict with keys: license, license_name, license_link.
    
    Fetches the license from the original HuggingFace model to ensure quantized
    models inherit the correct license from their base model.
    """
    if is_tool:
        return {
            "license": "other",
            "license_name": "other",
            "license_link": _license_link_for(model_path, is_hf_model),
        }

    if _is_mistral_research_model(model_path):
        license_info = MISTRAL_RESEARCH_LICENSE.copy()
        if license_info.get("license_link") == "LICENSE" and is_hf_model:
            license_info["license_link"] = _license_link_for(model_path, is_hf_model)
        return license_info

    if _is_qwen_license_model(model_path):
        return QWEN_LICENSE.copy()

    # Try to fetch license from the base model on HuggingFace
    if is_hf_model:
        fetched = fetch_license_from_hf(model_path)
        if fetched:
            print(f"[license] Using license from base model {model_path}: {fetched['license']}")
            return fetched

    # Fallback: use 'other' and link to the base model's LICENSE file
    # This ensures we don't incorrectly assign a license
    return {
        "license": "other",
        "license_name": "other",
        "license_link": _license_link_for(model_path, is_hf_model),
    }


__all__ = [
    "resolve_template_name",
    "compute_license_info",
    "fetch_license_from_hf",
]

