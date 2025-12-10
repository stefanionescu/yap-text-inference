"""Classifier inference backends (PyTorch + optional ONNX)."""

from __future__ import annotations

import logging
from pathlib import Path
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


class OnnxClassifierBackend:
    """ONNX Runtime backend with optional CUDA execution provider."""

    def __init__(
        self,
        info: ClassifierModelInfo,
        *,
        onnx_path: Path,
    ) -> None:
        try:
            import onnxruntime as ort  # type: ignore[import]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "onnxruntime is required for TOOL_USE_ONNX"
            ) from exc

        self._info = info
        self._tokenizer = AutoTokenizer.from_pretrained(
            info.model_id,
            trust_remote_code=True,
        )
        self._tokenizer.truncation_side = "left"
        tokenizer_max = getattr(self._tokenizer, "model_max_length", info.max_length)
        self._max_length = min(info.max_length, tokenizer_max or info.max_length)

        providers: list[Any] = []
        available = set(ort.get_available_providers())
        if "CUDAExecutionProvider" in available:
            providers.append(
                (
                    "CUDAExecutionProvider",
                    {
                        "device_id": 0,
                        "arena_extend_strategy": "kNextPowerOfTwo",
                        "do_copy_in_default_stream": True,
                    },
                )
            )
        providers.append("CPUExecutionProvider")

        self._session = ort.InferenceSession(
            str(onnx_path),
            providers=providers,
        )

    def infer(self, texts: list[str]) -> torch.Tensor:
        enc = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_length,
        )
        ort_inputs = {
            "input_ids": enc["input_ids"].cpu().numpy(),
            "attention_mask": enc["attention_mask"].cpu().numpy(),
        }
        if self._info.model_type == "longformer":
            global_mask = torch.zeros_like(enc["input_ids"])
            global_mask[:, 0] = 1
            ort_inputs["global_attention_mask"] = global_mask.cpu().numpy()

        outputs = self._session.run(None, ort_inputs)
        return torch.from_numpy(outputs[0])


def export_model_to_onnx(
    info: ClassifierModelInfo,
    *,
    onnx_path: Path,
    opset: int,
) -> None:
    """Export the classifier checkpoint to ONNX format (idempotent)."""
    logger.info("classifier: exporting ONNX model to %s", onnx_path)

    tokenizer = AutoTokenizer.from_pretrained(info.model_id, trust_remote_code=True)
    tokenizer.truncation_side = "left"
    tokenizer_max = getattr(tokenizer, "model_max_length", info.max_length)
    max_length = min(info.max_length, tokenizer_max or info.max_length)

    dummy = tokenizer(
        ["dummy input for onnx export"],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=max_length,
    )

    input_names = ["input_ids", "attention_mask"]
    dynamic_axes = {
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "logits": {0: "batch"},
    }

    if info.model_type == "longformer":
        global_mask = torch.zeros_like(dummy["input_ids"])
        global_mask[:, 0] = 1
        dummy["global_attention_mask"] = global_mask
        input_names.append("global_attention_mask")
        dynamic_axes["global_attention_mask"] = {0: "batch", 1: "seq"}

    model = AutoModelForSequenceClassification.from_pretrained(
        info.model_id,
        trust_remote_code=True,
    )
    model.eval()
    model.to("cpu")

    with torch.inference_mode():
        torch.onnx.export(
            model,
            tuple(dummy[name] for name in input_names),
            onnx_path,
            input_names=input_names,
            output_names=["logits"],
            dynamic_axes=dynamic_axes,
            opset_version=opset,
            do_constant_folding=True,
        )

    try:
        import onnx  # type: ignore[import]

        onnx.checker.check_model(onnx.load(str(onnx_path)))
    except Exception as exc:  # noqa: BLE001
        onnx_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to validate exported ONNX model: {exc}") from exc


__all__ = [
    "TorchClassifierBackend",
    "OnnxClassifierBackend",
    "export_model_to_onnx",
]
