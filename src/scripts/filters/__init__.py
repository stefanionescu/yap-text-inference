"""Log filtering and noise suppression entry point.

This module orchestrates log filtering across multiple libraries:
- HuggingFace Hub: Download/upload progress bars
- Transformers: Logging verbosity and progress bars
- TensorRT-LLM: Noise suppression via stream filters
- vLLM: Engine initialization and worker process output
- LLMCompressor/AutoAWQ: Calibration progress bars
- Tool: Warmup logs and pip install output

Controlled by environment variables:
- SHOW_HF_LOGS: Enable HuggingFace progress bars (default: False)
- SHOW_TRT_LOGS: Enable TensorRT-LLM verbose output (default: False)
- SHOW_VLLM_LOGS: Enable vLLM engine initialization output (default: False)
- SHOW_LLMCOMPRESSOR_LOGS: Enable LLMCompressor/AutoAWQ calibration output (default: False)
- SHOW_TOOL_LOGS: Enable tool warmup and install output (default: False)

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
from src.helpers.env import env_flag
from . import (
    hf as hf_filters,
    trt as trt_filters,
    tool as tool_filters,
    vllm as vllm_filters,
    transformers as transformers_filters,
    llmcompressor as llmcompressor_filters,
)

logger = logging.getLogger("log_filter")

_STATE = {"configured": False}


def configure_hf_logging(disable_downloads: bool = True, disable_uploads: bool = True) -> None:
    """Configure HuggingFace logging."""
    hf_filters.configure_hf_logging(disable_downloads, disable_uploads)


def configure_transformers_logging() -> None:
    """Configure transformers logging."""
    transformers_filters.configure_transformers_logging()


def configure_trt_logging() -> None:
    """Configure TensorRT-LLM logging."""
    trt_filters.configure_trt_logging()


def configure_vllm_logging() -> None:
    """Configure vLLM logging."""
    vllm_filters.configure_vllm_logging()


def configure_llmcompressor_logging() -> None:
    """Configure LLMCompressor/AutoAWQ logging."""
    llmcompressor_filters.configure_llmcompressor_logging()


def configure_tool_logging() -> None:
    """Configure tool logging."""
    tool_filters.configure_tool_logging()


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

    # Tool noise suppression
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
