"""HuggingFace Hub log filtering.

Controls visibility of HuggingFace download/upload progress bars.
"""

from __future__ import annotations

import os
import logging
import contextlib
from typing import cast
from collections.abc import Iterable
from src.config.filters import HF_ALL_GROUPS, HF_UPLOAD_GROUPS, HF_DOWNLOAD_GROUPS

logger = logging.getLogger("log_filter")


def label_hf_snapshot_progress(group: str) -> None:
    """Tag HuggingFace snapshot download bars so they can be disabled by group.

    This patches the tqdm class used by huggingface_hub to add a 'name' kwarg
    to snapshot download progress bars, allowing them to be selectively disabled.
    """
    try:
        import huggingface_hub.utils as utils_module  # noqa: PLC0415
        import huggingface_hub.utils.tqdm as tqdm_module  # noqa: PLC0415
        import huggingface_hub._snapshot_download as snapshot_module  # noqa: PLC0415
    except ModuleNotFoundError:
        return

    base_tqdm = getattr(tqdm_module, "tqdm", None)
    if base_tqdm is None:
        return

    # Avoid wrapping multiple times if the module gets reloaded (e.g. in tests)
    if getattr(base_tqdm, "__dict__", {}).get("_log_filter_patched"):
        return

    base_tqdm_type = cast(type, base_tqdm)

    class SnapshotQuietTqdm(base_tqdm_type):  # type: ignore[misc,valid-type]
        _log_filter_patched = True

        def __init__(self, *args, **kwargs):
            desc = kwargs.get("desc")
            if desc and desc.startswith("Fetching"):
                kwargs.setdefault("name", group)
            super().__init__(*args, **kwargs)

    tqdm_module.tqdm = SnapshotQuietTqdm
    utils_module.tqdm = SnapshotQuietTqdm

    # Snapshot download stores a direct reference when imported, so update it too
    if hasattr(snapshot_module, "hf_tqdm"):
        snapshot_module.hf_tqdm = SnapshotQuietTqdm


def disable_hf_progress(groups: Iterable[str]) -> None:
    """Disable HuggingFace progress bars for specified groups."""
    try:
        import huggingface_hub.utils as hub_utils  # noqa: PLC0415
    except ModuleNotFoundError:
        return

    disable = getattr(hub_utils, "disable_progress_bars", None)
    if disable is None:
        return

    for name in groups:
        try:
            disable(name)
        except Exception as exc:  # pragma: no cover
            logger.debug("failed to disable HF progress for %s: %s", name, exc)


def enable_hf_progress(groups: Iterable[str] | None = None) -> None:
    """Re-enable HuggingFace progress bars for specified groups.

    Args:
        groups: Specific groups to enable, or None for all groups.
    """
    # Clear env vars that disable progress
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
    os.environ.pop("TQDM_DISABLE", None)

    try:
        from huggingface_hub.utils import enable_progress_bars  # noqa: PLC0415
    except ImportError:
        return

    target_groups = groups if groups is not None else HF_ALL_GROUPS

    for group in target_groups:
        with contextlib.suppress(Exception):
            enable_progress_bars(group)

    # Also enable globally as fallback
    with contextlib.suppress(Exception):
        enable_progress_bars()


def configure_hf_logging(
    disable_downloads: bool = True,
    disable_uploads: bool = True,
) -> None:
    """Configure HuggingFace Hub logging.

    Args:
        disable_downloads: Disable download progress bars.
        disable_uploads: Disable upload progress bars.
    """
    # Label snapshot progress bars so they can be disabled
    snapshot_group = "huggingface_hub.snapshot_download"
    label_hf_snapshot_progress(snapshot_group)

    # Disable requested groups
    if disable_downloads:
        disable_hf_progress(HF_DOWNLOAD_GROUPS)
    if disable_uploads:
        disable_hf_progress(HF_UPLOAD_GROUPS)


__all__ = [
    "configure_hf_logging",
    "enable_hf_progress",
    "disable_hf_progress",
    "label_hf_snapshot_progress",
]
