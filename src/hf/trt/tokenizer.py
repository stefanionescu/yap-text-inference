"""Tokenizer discovery helpers for TRT HuggingFace uploads."""

from __future__ import annotations

from pathlib import Path

from src.config.quantization import TOKENIZER_FILES
from src.config.trt import TRT_CHECKPOINT_SUFFIXES, TRT_TOKENIZER_CONFIG_FILE


def _has_tokenizer(directory: Path) -> bool:
    return (directory / TRT_TOKENIZER_CONFIG_FILE).exists()


def _extract_model_stem(checkpoint_name: str) -> str:
    for suffix in TRT_CHECKPOINT_SUFFIXES:
        if checkpoint_name.endswith(suffix):
            return checkpoint_name[: -len(suffix)]
    return checkpoint_name


def _find_hf_dir_in_path(parent: Path, model_stem: str) -> Path | None:
    candidate = parent / f"{model_stem}-hf"
    if candidate.is_dir() and _has_tokenizer(candidate):
        return candidate
    return None


def _download_tokenizer_from_hub(base_model: str) -> Path | None:
    try:
        import tempfile

        from huggingface_hub import snapshot_download

        temp_dir = Path(tempfile.mkdtemp(prefix="tokenizer_"))
        snapshot_download(
            repo_id=base_model,
            local_dir=str(temp_dir),
            allow_patterns=list(TOKENIZER_FILES),
        )
        if _has_tokenizer(temp_dir):
            return temp_dir
    except Exception as exc:  # noqa: BLE001
        print(f"[trt-hf] Warning: Failed to download tokenizer from {base_model}: {exc}")
    return None


def find_tokenizer_dir(checkpoint_dir: Path, base_model: str | None) -> Path | None:
    """Find tokenizer files near the checkpoint, downloading if necessary."""
    if _has_tokenizer(checkpoint_dir):
        return checkpoint_dir

    model_stem = _extract_model_stem(checkpoint_dir.name)

    sibling = _find_hf_dir_in_path(checkpoint_dir.parent, model_stem)
    if sibling:
        return sibling

    workspace_models = checkpoint_dir.parent.parent / "models"
    if workspace_models.is_dir():
        workspace_match = _find_hf_dir_in_path(workspace_models, model_stem)
        if workspace_match:
            return workspace_match

    if base_model:
        return _download_tokenizer_from_hub(base_model)

    return None


__all__ = ["find_tokenizer_dir"]
