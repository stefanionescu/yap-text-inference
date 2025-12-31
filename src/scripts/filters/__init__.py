"""Log filtering and noise suppression entry point.

This module orchestrates log filtering across multiple libraries:
- HuggingFace Hub: Download/upload progress bars
- Transformers: Logging verbosity and progress bars
- TensorRT-LLM: Noise suppression via stream filters
- LLMCompressor/AutoAWQ: Calibration progress bars

Controlled by environment variables:
- SHOW_HF_LOGS: Enable HuggingFace progress bars (default: False)
- SHOW_TRT_LOGS: Enable TensorRT-LLM verbose output (default: False)
- SHOW_LLMCOMPRESSOR_LOGS: Enable LLMCompressor/AutoAWQ calibration output (default: False)

Usage:
    # Call configure() early, before other libraries are imported
    from src.scripts.filters import configure
    configure()

    # Or import individual modules for fine-grained control
    from src.scripts.filters.hf import configure_hf_logging
    from src.scripts.filters.trt import configure_trt_logging
    from src.scripts.filters.llmcompressor import configure_llmcompressor_logging
"""

from __future__ import annotations

import logging

from src.helpers.env import env_flag

# Lazy imports to avoid triggering huggingface_hub on package import
# These are imported when needed by configure()
_hf_module = None
_transformers_module = None
_trt_module = None
_llmcompressor_module = None

logger = logging.getLogger("log_filter")

# Track if configuration has been applied
_configured = False


def configure_hf_logging(disable_downloads: bool = True, disable_uploads: bool = True) -> None:
    """Configure HuggingFace logging (lazy import)."""
    global _hf_module
    if _hf_module is None:
        from . import hf as _hf_module_local
        _hf_module = _hf_module_local
    _hf_module.configure_hf_logging(disable_downloads, disable_uploads)


def configure_transformers_logging() -> None:
    """Configure transformers logging (lazy import)."""
    global _transformers_module
    if _transformers_module is None:
        from . import transformers as _transformers_module_local
        _transformers_module = _transformers_module_local
    _transformers_module.configure_transformers_logging()


def configure_trt_logging() -> None:
    """Configure TensorRT-LLM logging (lazy import)."""
    global _trt_module
    if _trt_module is None:
        from . import trt as _trt_module_local
        _trt_module = _trt_module_local
    _trt_module.configure_trt_logging()


def configure_llmcompressor_logging() -> None:
    """Configure LLMCompressor/AutoAWQ logging (lazy import)."""
    global _llmcompressor_module
    if _llmcompressor_module is None:
        from . import llmcompressor as _llmcompressor_module_local
        _llmcompressor_module = _llmcompressor_module_local
    _llmcompressor_module.configure_llmcompressor_logging()


def configure() -> None:
    """Apply all log filters based on environment configuration.
    
    This is the main entry point for log filtering. Call this early
    in the application lifecycle before other libraries are imported.
    
    Safe to call multiple times - subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return
    _configured = True

    show_hf_logs = env_flag("SHOW_HF_LOGS", False)
    show_trt_logs = env_flag("SHOW_TRT_LOGS", False)
    show_llmcompressor_logs = env_flag("SHOW_LLMCOMPRESSOR_LOGS", False)

    # HuggingFace progress bars
    if not show_hf_logs:
        configure_hf_logging(disable_downloads=True, disable_uploads=True)
    else:
        logger.debug("HF logs enabled via SHOW_HF_LOGS")

    # Transformers verbosity/progress (always quiet, independent of HF)
    configure_transformers_logging()

    # TensorRT-LLM noise suppression
    if not show_trt_logs:
        configure_trt_logging()
    else:
        logger.debug("TRT logs enabled via SHOW_TRT_LOGS")

    # LLMCompressor/AutoAWQ calibration noise suppression
    if not show_llmcompressor_logs:
        configure_llmcompressor_logging()
    else:
        logger.debug("LLMCompressor logs enabled via SHOW_LLMCOMPRESSOR_LOGS")


__all__ = [
    "configure",
    "configure_hf_logging",
    "configure_transformers_logging",
    "configure_trt_logging",
    "configure_llmcompressor_logging",
]

