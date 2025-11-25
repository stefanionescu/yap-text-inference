"""Shared helpers for AWQ quantization routines."""

from __future__ import annotations

import os
import time
from typing import Any


def requires_autoawq_backend(model_config: Any | None, model_identifier: str) -> bool:
    """Return True when this model must be quantized with AutoAWQ."""

    from src.config.awq import normalize_model_id  # lazy import to avoid cycles

    model_type = (getattr(model_config, "model_type", "") or "").lower()
    if model_type.startswith("qwen"):
        return True

    if not model_type:
        normalized = normalize_model_id(model_identifier)
        qwen_markers = ("qwen3", "qwen2", "qwen")
        if any(marker in normalized for marker in qwen_markers):
            return True

    return False


def ensure_autoawq_dependencies() -> None:
    """Backfill legacy symbols expected by AutoAWQ on newer transformers builds."""

    try:
        from transformers import activations  # type: ignore

        getattr(activations, "PytorchGELUTanh")
    except Exception:
        import torch.nn as nn
        from transformers import activations  # type: ignore

        class PytorchGELUTanh(nn.Module):  # type: ignore
            def forward(self, hidden_states: Any) -> Any:  # type: ignore[override]
                import torch

                return torch.nn.functional.gelu(hidden_states, approximate="tanh")

        activations.PytorchGELUTanh = PytorchGELUTanh  # type: ignore[attr-defined]


def prefetch_model(model_path: str) -> str | None:
    """Resolve remote HF repos to a local snapshot for robustness."""

    resolved_model_path = model_path
    if os.path.isdir(model_path) or "/" not in model_path:
        return resolved_model_path

    try:
        from huggingface_hub import snapshot_download  # lazy import
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import huggingface_hub for snapshot download: {exc}")
        return None

    token = os.environ.get("HUGGINGFACE_HUB_TOKEN") or os.environ.get("HF_TOKEN")
    cache_dir = os.environ.get("HF_HOME")

    print(f"[awq] Prefetching model from Hub: {model_path}")
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            resolved_model_path = snapshot_download(
                repo_id=model_path,
                token=token,
                local_files_only=False,
                resume_download=True,
                cache_dir=cache_dir,
            )
            last_err = None
            break
        except Exception as dl_err:  # noqa: BLE001
            last_err = dl_err
            backoff = min(2**attempt, 5)
            print(f"[awq] Hub download failed (attempt {attempt}/3): {dl_err}")
            if attempt < 3:
                print(f"[awq] Retrying in {backoff}s…")
                time.sleep(backoff)

    if last_err is not None:
        print(
            "[awq] Quantization failed: could not download model from Hugging Face. "
            "Check network access, repository visibility, and set HF_TOKEN or "
            "HUGGINGFACE_HUB_TOKEN if needed."
        )
        return None

    return resolved_model_path


def load_model_config(model_path: str) -> Any | None:
    """Best-effort load of model config for seqlen validation."""

    try:
        from transformers import AutoConfig  # type: ignore
    except Exception:
        return None

    try:
        return AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: unable to load config for {model_path}: {exc}")
        return None


