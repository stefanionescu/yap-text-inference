"""
Monkey-patch for transformers 4.56.0 + Python 3.10 compatibility.

The auto_docstring feature in transformers 4.56.0 crashes when processing
models that use Python 3.10+ union type syntax (X | Y) in type annotations
(e.g., Kimi Linear models).

Error: AttributeError: 'types.UnionType' object has no attribute '__name__'

This patch wraps the problematic function to handle UnionType gracefully.

Usage:
    import src.helpers.transformers  # at top of script
    # or
    from src.helpers.transformers import patch_transformers_auto_docstring
    patch_transformers_auto_docstring()
"""

from __future__ import annotations

import sys


def patch_transformers_auto_docstring() -> bool:
    """Patch transformers auto_docstring to handle Python 3.10+ union types."""
    try:
        import transformers.utils.auto_docstring as ad
    except ImportError:
        return False

    # Check if already patched
    if getattr(ad, "_patched_for_union_type", False):
        return True

    original_func = ad._process_parameter_type

    def patched_process_parameter_type(param, param_name, func):
        """Wrapped version that handles types.UnionType gracefully."""
        try:
            return original_func(param, param_name, func)
        except AttributeError as e:
            if "UnionType" in str(e) and "__name__" in str(e):
                # Return a safe fallback for union types
                return "Any", True
            raise

    ad._process_parameter_type = patched_process_parameter_type
    ad._patched_for_union_type = True

    return True


# Apply patch on import
if patch_transformers_auto_docstring():
    print(
        "[patch] Applied transformers auto_docstring fix for Python 3.10 union types",
        file=sys.stderr,
    )

