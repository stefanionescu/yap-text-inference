"""
Monkey-patch for transformers 4.56.0 + Python 3.10 compatibility.

The auto_docstring feature in transformers 4.56.0 crashes when processing
models that use Python 3.10+ union type syntax (X | Y) in type annotations
(e.g., Kimi Linear models).

Error: AttributeError: 'types.UnionType' object has no attribute '__name__'

The bug is in _process_parameter_type where it checks hasattr(__name__) but
types.UnionType doesn't have __name__, causing the crash.

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


# Apply patch on import
if patch_transformers_auto_docstring():
    print(
        "[patch] Applied transformers auto_docstring fix for Python 3.10 union types",
        file=sys.stderr,
    )

