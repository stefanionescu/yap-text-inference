"""Tool inference backend (PyTorch).

This module provides the PyTorch-based inference backend for the
tool adapter. It handles:

1. Model Loading:
   - AutoModelForSequenceClassification for any HuggingFace model
   - Automatic dtype selection (float16 for GPU, float32 for CPU)
   - trust_remote_code for custom model implementations

2. Tokenization:
   - AutoTokenizer with left-side truncation
   - Batch tokenization with padding
   - Respect max_length from model config

3. Inference:
   - BERT-style forward pass
   - Longformer global attention mask support
   - torch.inference_mode() for efficiency

4. Optimization:
   - Optional torch.compile() for speedup
   - TF32 and cuDNN benchmark for CUDA
   - Gradient disabled globally
"""

from __future__ import annotations

import torch
import logging
from src.state import ToolModelInfo
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


class TorchToolBackend:
    """PyTorch backend supporting both BERT-style and Longformer models.

    This class handles the actual model loading and inference, supporting
    various transformer architectures for sequence classification.

    Attributes:
        _info: Model metadata (type, max_length, num_labels).
        _device: Target device string.
        _dtype: Torch dtype for inference.
        _tokenizer: HuggingFace tokenizer instance.
        _model: The loaded classification model.
        _max_length: Effective max sequence length.
    """

    def __init__(
        self,
        info: ToolModelInfo,
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
        tokenizer_max = getattr(self._tokenizer, "model_max_length", None)
        self._max_length = min(info.max_length, tokenizer_max) if tokenizer_max else info.max_length

        self._model = (
            AutoModelForSequenceClassification.from_pretrained(
                info.model_id,
                torch_dtype=dtype if device.startswith("cuda") else None,
                trust_remote_code=True,
            )
            .to(device=device, dtype=dtype)
            .eval()
        )

        if device.startswith("cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.benchmark = True

        if compile_model and hasattr(torch, "compile"):
            try:
                self._model = torch.compile(self._model)
                logger.info("tool: enabled torch.compile for %s", info.model_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tool: torch.compile failed, running eager: %s",
                    exc,
                )

    def infer(self, texts: list[str]) -> torch.Tensor:
        """Run inference on a batch of texts.

        Tokenizes inputs, runs the model, and returns logits.
        Handles Longformer global attention masks automatically.

        Args:
            texts: List of input texts to classify.

        Returns:
            Tensor of shape (batch_size, num_labels) containing logits.
        """
        enc = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_length,
            pad_to_multiple_of=8,
        )
        enc = {k: v.to(self._device) for k, v in enc.items()}

        with torch.inference_mode():
            if self._info.model_type == "longformer":
                # Longformer requires global attention on CLS token (index 0)
                global_mask = torch.zeros_like(enc["input_ids"])
                global_mask[:, 0] = 1
                outputs = self._model(
                    **enc,
                    global_attention_mask=global_mask,
                )
            else:
                outputs = self._model(**enc)
            return outputs.logits

    @property
    def max_length(self) -> int:
        """Return effective backend max sequence length after tokenizer clamp."""
        return self._max_length


__all__ = [
    "TorchToolBackend",
]
