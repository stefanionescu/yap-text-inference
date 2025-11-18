"""SNAC model wrapper utilities."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from server.config import settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from snac import SNAC as SNACModel  # noqa: N811
    from torch import Tensor as TorchTensor
else:
    SNACModel = Any
    TorchTensor = Any

torch = importlib.import_module("torch")
SNAC = importlib.import_module("snac").SNAC

SNAC_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class SnacProcessor:
    """Handles SNAC model operations with batching optimization."""

    def __init__(self):
        self.dtype_decoder = torch.float32
        self.model = self._initialize_model()
        self.stream = torch.cuda.Stream(device=torch.device(SNAC_DEVICE)) if torch.cuda.is_available() else None

    def _initialize_model(self) -> SNACModel:
        model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(SNAC_DEVICE)
        model.decoder = model.decoder.to(self.dtype_decoder)

        if settings.snac_torch_compile:
            model.decoder = torch.compile(model.decoder, dynamic=True)
            model.quantizer = torch.compile(model.quantizer, dynamic=True)

        return model

    def process_batch(self, codes_list: list[list[TorchTensor]]) -> list[TorchTensor]:
        """Decode a batch of code triplets into audio tensors."""
        with torch.inference_mode():
            if self.stream is not None:
                outputs = self._process_batch_cuda(codes_list)
                torch.cuda.synchronize()
                return outputs
            return self._process_batch_cpu(codes_list)

    def _process_batch_cuda(self, codes_list: list[list[TorchTensor]]) -> list[TorchTensor]:
        if self.stream is None:
            return self._decode_codes_batch(codes_list)
        with torch.cuda.stream(self.stream):
            return self._decode_codes_batch(codes_list)

    def _process_batch_cpu(self, codes_list: list[list[TorchTensor]]) -> list[TorchTensor]:
        return self._decode_codes_batch(codes_list)

    def _decode_codes_batch(self, codes_list: list[list[TorchTensor]]) -> list[TorchTensor]:
        shapes = [(c[0].shape, c[1].shape, c[2].shape) for c in codes_list]
        can_concatenate = len(set(shapes)) == 1

        if can_concatenate and len(codes_list) > 1:
            c0 = torch.cat([c[0] for c in codes_list], dim=0)
            c1 = torch.cat([c[1] for c in codes_list], dim=0)
            c2 = torch.cat([c[2] for c in codes_list], dim=0)
            z_q = self.model.quantizer.from_codes([c0, c1, c2])
            audio_hat = self.model.decoder(z_q.to(self.dtype_decoder))[
                :, :, settings.snac_decode_crop_start : settings.snac_decode_crop_end
            ]
            return list(audio_hat.split(1, dim=0))

        outputs: list[TorchTensor] = []
        for c0, c1, c2 in codes_list:
            z_q = self.model.quantizer.from_codes([c0, c1, c2])
            outputs.append(
                self.model.decoder(z_q.to(self.dtype_decoder))[
                    :, :, settings.snac_decode_crop_start : settings.snac_decode_crop_end
                ]
            )
        return outputs
