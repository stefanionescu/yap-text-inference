"""Log filtering and noise suppression entry point.

This module orchestrates log filtering across multiple libraries:
- HuggingFace Hub: Download/upload progress bars
- Transformers: Logging verbosity and progress bars
- TensorRT-LLM: Noise suppression via stream filters
- vLLM: Engine initialization and worker process output
- LLMCompressor/AutoAWQ: Calibration progress bars
- Tool classifier: Warmup logs and pip install output

Controlled by environment variables:
- SHOW_HF_LOGS: Enable HuggingFace progress bars (default: False)
- SHOW_TRT_LOGS: Enable TensorRT-LLM verbose output (default: False)
- SHOW_VLLM_LOGS: Enable vLLM engine initialization output (default: False)
- SHOW_LLMCOMPRESSOR_LOGS: Enable LLMCompressor/AutoAWQ calibration output (default: False)
- SHOW_TOOL_LOGS: Enable tool classifier warmup and install output (default: False)

Usage:
    # Call configure() early, before other libraries are imported
    from src.scripts.filters import configure
    configure()

    # Or import individual modules for fine-grained control
    from src.scripts.filters.hf import configure_hf_logging
    from src.scripts.filters.trt import configure_trt_logging
    from src.scripts.filters.vllm import configure_vllm_logging
    from src.scripts.filters.llmcompressor import configure_llmcompressor_logging
    from src.scripts.filters.tool import configure_tool_logging
"""

from __future__ import annotations

import logging
from typing import Any

from src.helpers.env import env_flag

logger = logging.getLogger("log_filter")

# Lazy imports to avoid triggering huggingface_hub on package import
# These are imported when needed by configure()
_STATE: dict[str, Any] = {
    "hf": None,
    "transformers": None,
    "trt": None,
    "vllm": None,
    "llmcompressor": None,
    "tool": None,
    "configured": False,
}


def configure_hf_logging(disable_downloads: bool = True, disable_uploads: bool = True) -> None:
    """Configure HuggingFace logging (lazy import)."""
    if _STATE["hf"] is None:
        from . import hf as _hf_module_local  # noqa: PLC0415

        _STATE["hf"] = _hf_module_local
    _STATE["hf"].configure_hf_logging(disable_downloads, disable_uploads)


def configure_transformers_logging() -> None:
    """Configure transformers logging (lazy import)."""
    if _STATE["transformers"] is None:
        from . import transformers as _transformers_module_local  # noqa: PLC0415

        _STATE["transformers"] = _transformers_module_local
    _STATE["transformers"].configure_transformers_logging()


def configure_trt_logging() -> None:
    """Configure TensorRT-LLM logging (lazy import)."""
    if _STATE["trt"] is None:
        from . import trt as _trt_module_local  # noqa: PLC0415

        _STATE["trt"] = _trt_module_local
    _STATE["trt"].configure_trt_logging()


def configure_vllm_logging() -> None:
    """Configure vLLM logging (lazy import)."""
    if _STATE["vllm"] is None:
        from . import vllm as _vllm_module_local  # noqa: PLC0415

        _STATE["vllm"] = _vllm_module_local
    _STATE["vllm"].configure_vllm_logging()


def configure_llmcompressor_logging() -> None:
    """Configure LLMCompressor/AutoAWQ logging (lazy import)."""
    if _STATE["llmcompressor"] is None:
        from . import llmcompressor as _llmcompressor_module_local  # noqa: PLC0415

        _STATE["llmcompressor"] = _llmcompressor_module_local
    _STATE["llmcompressor"].configure_llmcompressor_logging()


def configure_tool_logging() -> None:
    """Configure tool classifier logging (lazy import)."""
    if _STATE["tool"] is None:
        from . import tool as _tool_module_local  # noqa: PLC0415

        _STATE["tool"] = _tool_module_local
    _STATE["tool"].configure_tool_logging()


def configure() -> None:
    """Apply all log filters based on environment configuration.

    This is the main entry point for log filtering. Call this early
    in the application lifecycle before other libraries are imported.

    Safe to call multiple times - subsequent calls are no-ops.
    """
    if _STATE["configured"]:
        return
    _STATE["configured"] = True

    show_hf_logs = env_flag("SHOW_HF_LOGS", False)
    show_trt_logs = env_flag("SHOW_TRT_LOGS", False)
    show_vllm_logs = env_flag("SHOW_VLLM_LOGS", False)
    show_llmcompressor_logs = env_flag("SHOW_LLMCOMPRESSOR_LOGS", False)
    show_tool_logs = env_flag("SHOW_TOOL_LOGS", False)

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

    # vLLM engine initialization noise suppression
    if not show_vllm_logs:
        configure_vllm_logging()
    else:
        logger.debug("vLLM logs enabled via SHOW_VLLM_LOGS")

    # LLMCompressor/AutoAWQ calibration noise suppression
    if not show_llmcompressor_logs:
        configure_llmcompressor_logging()
    else:
        logger.debug("LLMCompressor logs enabled via SHOW_LLMCOMPRESSOR_LOGS")

    # Tool classifier noise suppression
    if not show_tool_logs:
        configure_tool_logging()
    else:
        logger.debug("Tool logs enabled via SHOW_TOOL_LOGS")


__all__ = [
    "configure",
    "configure_hf_logging",
    "configure_transformers_logging",
    "configure_trt_logging",
    "configure_vllm_logging",
    "configure_llmcompressor_logging",
    "configure_tool_logging",
]
