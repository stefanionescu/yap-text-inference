"""Classifier inference backend (PyTorch)."""

from __future__ import annotations

import logging
from typing import Any

import torch  # type: ignore[import]
from transformers import (  # type: ignore[import]
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from .model_info import ClassifierModelInfo

logger = logging.getLogger(__name__)


class TorchClassifierBackend:
    """PyTorch backend supporting both BERT-style and Longformer models."""

    def __init__(
        self,
        info: ClassifierModelInfo,
        *,
        device: str,
        dtype: torch.dtype,
        compile_model: bool,
    ) -> None:
        self._info = info
        self._device = device
        self._dtype = dtype

        self._tokenizer = AutoTokenizer.from_pretrained(
            info.model_id,
            trust_remote_code=True,
        )
        self._tokenizer.truncation_side = "left"
        tokenizer_max = getattr(self._tokenizer, "model_max_length", info.max_length)
        self._max_length = min(info.max_length, tokenizer_max or info.max_length)

        model_kwargs: dict[str, Any] = {"trust_remote_code": True}
        if device.startswith("cuda"):
            model_kwargs["torch_dtype"] = dtype

        self._model = AutoModelForSequenceClassification.from_pretrained(
            info.model_id,
            **model_kwargs,
        )
        self._model.to(device=device, dtype=dtype)
        self._model.eval()

        torch.set_grad_enabled(False)
        if device.startswith("cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.benchmark = True

        if compile_model and hasattr(torch, "compile"):
            try:
                self._model = torch.compile(self._model)  # type: ignore[arg-type]
                logger.info("classifier: enabled torch.compile for %s", info.model_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "classifier: torch.compile failed, running eager: %s",
                    exc,
                )

    def infer(self, texts: list[str]) -> torch.Tensor:
        enc = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_length,
        )
        enc = {k: v.to(self._device) for k, v in enc.items()}

        with torch.inference_mode():
            if self._info.model_type == "longformer":
                global_mask = torch.zeros_like(enc["input_ids"])
                global_mask[:, 0] = 1
                outputs = self._model(
                    **enc,
                    global_attention_mask=global_mask.to(self._device),
                )
            else:
                outputs = self._model(**enc)
            return outputs.logits


__all__ = [
    "TorchClassifierBackend",
]
