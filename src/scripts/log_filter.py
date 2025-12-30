"""Project-wide log filtering and noise suppression.

Imported early in the application lifecycle to reduce log noise from
third-party libraries like Hugging Face and Transformers.
"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Iterable


def _label_hf_snapshot_progress(group: str) -> None:
    """Tag Hugging Face snapshot download bars so they can be disabled by group."""

    try:
        tqdm_module = importlib.import_module("huggingface_hub.utils.tqdm")
        utils_module = importlib.import_module("huggingface_hub.utils")
        snapshot_module = importlib.import_module("huggingface_hub._snapshot_download")
    except ModuleNotFoundError:
        return

    base_tqdm = getattr(tqdm_module, "tqdm", None)
    if base_tqdm is None:
        return

    # Avoid wrapping multiple times if the module gets reloaded (e.g. in tests)
    if getattr(base_tqdm, "__dict__", {}).get("_log_filter_patched"):
        return

    class SnapshotQuietTqdm(base_tqdm):
        _log_filter_patched = True

        def __init__(self, *args, **kwargs):
            desc = kwargs.get("desc")
            if desc and desc.startswith("Fetching"):
                kwargs.setdefault("name", group)
            super().__init__(*args, **kwargs)

    tqdm_module.tqdm = SnapshotQuietTqdm
    setattr(utils_module, "tqdm", SnapshotQuietTqdm)

    # Snapshot download stores a direct reference when imported, so update it too
    if hasattr(snapshot_module, "hf_tqdm"):
        snapshot_module.hf_tqdm = SnapshotQuietTqdm


def _disable_hf_download_progress(groups: Iterable[str]) -> None:
    """Disable Hugging Face download progress bars without touching uploads."""
    try:
        hub_utils = importlib.import_module("huggingface_hub.utils")
    except ModuleNotFoundError:
        return

    disable = getattr(hub_utils, "disable_progress_bars", None)
    if disable is None:
        return

    logger = logging.getLogger("log_filter")
    for name in groups:
        try:
            disable(name)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug("failed to disable Hugging Face progress for %s: %s", name, exc)


def _configure_transformers_logging() -> None:
    """Quiet transformers logging/progress bars if the library is installed."""

    try:
        from transformers.utils import logging as transformers_logging
    except ModuleNotFoundError:
        return

    logger = logging.getLogger("log_filter")

    try:
        transformers_logging.set_verbosity_warning()
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug("failed to set transformers verbosity: %s", exc)

    try:
        transformers_logging.disable_progress_bar()
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug("failed to disable transformers progress: %s", exc)

    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")


def _configure_trtllm_logging() -> None:
    """Suppress TensorRT-LLM and modelopt log noise during quantization."""
    import warnings

    # Suppress TensorRT-LLM loggers
    for logger_name in (
        "tensorrt_llm",
        "tensorrt_llm.logger",
        "tensorrt_llm.runtime",
        "modelopt",
        "modelopt.torch",
        "modelopt.torch.quantization",
        "nvidia_modelopt",
        "accelerate",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    # Suppress deprecation warnings from torch/modelopt
    warnings.filterwarnings("ignore", message=".*torch_dtype.*is deprecated.*")
    warnings.filterwarnings("ignore", message=".*Python version.*below the recommended.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="modelopt")
    warnings.filterwarnings("ignore", category=FutureWarning, module="modelopt")

    # Suppress TensorRT-LLM version banner via environment
    os.environ.setdefault("TRTLLM_LOG_LEVEL", "error")

    # Suppress datasets progress bars
    try:
        from datasets import disable_progress_bars as datasets_disable_progress
        datasets_disable_progress()
    except Exception:
        pass

    # Suppress tqdm progress bars globally for quantization
    os.environ.setdefault("TQDM_DISABLE", "1")


def _configure():
    snapshot_group = "huggingface_hub.snapshot_download"
    _label_hf_snapshot_progress(snapshot_group)

    download_groups = (
        "huggingface_hub.http_get",  # standard downloads (snapshot_download/hf_hub_download)
        "huggingface_hub.xet_get",   # Xet-accelerated downloads
        snapshot_group,               # parallel snapshot fetch progress
    )
    _disable_hf_download_progress(download_groups)
    _configure_transformers_logging()
    _configure_trtllm_logging()


_configure()

