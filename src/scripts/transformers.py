"""
Monkey-patches for transformers 4.56.0 + Python 3.10 compatibility.

Patches applied:
1. auto_docstring: Fix for Python 3.10+ union type syntax (X | Y)
   - Error: AttributeError: 'types.UnionType' object has no attribute '__name__'

2. attn_implementation: Force "eager" attention for custom models
   - Error: ValueError: Could not find the currently requested flash attention
     implementation at `None`. Make sure that you request a valid kernel from
     the hub, e.g. `kernels-community/flash-attn`.
   - Caused by transformers 4.56+ expecting flash attention as a Hub kernel
     while custom models (like Kimi) use the old flash attention interface.

Usage:
    import src.scripts.transformers  # at top of script
    # or
    from src.scripts.transformers import patch_transformers_auto_docstring
    patch_transformers_auto_docstring()
"""

from __future__ import annotations

import sys


def patch_transformers_auto_docstring() -> bool:
    """Patch transformers auto_docstring to handle Python 3.10+ union types."""
    try:
        # First, trigger the import to populate sys.modules
        from transformers.utils import auto_docstring  # noqa: F401

        # Get the actual module from sys.modules (not the decorator function)
        ad = sys.modules.get("transformers.utils.auto_docstring")
        if ad is None:
            return False
    except ImportError:
        return False

    # Check if already patched
    if getattr(ad, "_patched_for_union_type", False):
        return True

    # Find the function to patch
    if not hasattr(ad, "_process_parameter_type"):
        print("[patch] Warning: _process_parameter_type not found", file=sys.stderr)
        return False

    original_func = ad._process_parameter_type

    def patched_process_parameter_type(*args, **kwargs):
        """Wrapped version that handles types.UnionType gracefully."""
        try:
            return original_func(*args, **kwargs)
        except AttributeError as e:
            if "UnionType" in str(e) or "__name__" in str(e):
                # UnionType doesn't have __name__, return a safe fallback
                # Return type string and optional flag
                return "Any", True
            raise

    ad._process_parameter_type = patched_process_parameter_type
    ad._patched_for_union_type = True

    return True


def patch_attn_implementation_eager() -> bool:
    """
    Patch AutoModelForCausalLM.from_pretrained to default to eager attention.
    
    This fixes flash attention loading issues in transformers 4.56+ where
    custom models (like Kimi) request flash attention but the new Hub-based
    kernel loading fails with implementation path of `None`.
    
    By forcing eager attention, we avoid the flash attention code path entirely.
    """
    try:
        from transformers import AutoModelForCausalLM
    except ImportError:
        return False
    
    # Check if already patched
    if getattr(AutoModelForCausalLM, "_patched_eager_attn", False):
        return True
    
    original_from_pretrained = AutoModelForCausalLM.from_pretrained
    
    @classmethod
    def patched_from_pretrained(cls, pretrained_model_name_or_path, *args, **kwargs):
        """Force eager attention to avoid flash attention loading issues."""
        # Only force eager if not explicitly set by caller
        if "attn_implementation" not in kwargs:
            kwargs["attn_implementation"] = "eager"
        return original_from_pretrained.__func__(cls, pretrained_model_name_or_path, *args, **kwargs)
    
    AutoModelForCausalLM.from_pretrained = patched_from_pretrained
    AutoModelForCausalLM._patched_eager_attn = True
    
    return True


# Apply patches on import
if patch_transformers_auto_docstring():
    print(
        "[patch] Applied transformers auto_docstring fix for Python 3.10 union types",
        file=sys.stderr,
    )

if patch_attn_implementation_eager():
    print(
        "[patch] Applied transformers eager attention fix for flash attention loading",
        file=sys.stderr,
    )

