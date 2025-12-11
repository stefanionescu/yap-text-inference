"""Batched classifier adapter for screenshot intent detection."""

from __future__ import annotations

import logging
import torch  # type: ignore[import]

from .backend import TorchClassifierBackend
from .batch import BatchExecutor
from .model_info import ClassifierModelInfo, build_model_info

logger = logging.getLogger(__name__)


class ClassifierToolAdapter:
    """Microbatched classifier adapter for screenshot intent detection."""

    _memory_fraction_configured: set[int] = set()

    def __init__(
        self,
        model_path: str,
        *,
        threshold: float = 0.66,
        device: str | None = None,
        compile_model: bool = True,
        max_length: int = 1536,
        batch_max_size: int = 3,
        batch_max_delay_ms: float = 10.0,
        request_timeout_s: float = 5.0,
        gpu_memory_frac: float | None = None,
    ) -> None:
        self.model_path = model_path
        self.threshold = threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self.request_timeout_s = max(0.1, float(request_timeout_s))
        self._gpu_memory_frac = gpu_memory_frac

        self._configure_gpu_limit()
        self._model_info: ClassifierModelInfo = build_model_info(model_path, max_length)
        self._backend = TorchClassifierBackend(
            self._model_info,
            device=self.device,
            dtype=self.dtype,
            compile_model=compile_model,
        )
        self._batch = BatchExecutor(
            self._backend.infer,
            max_batch_size=batch_max_size,
            max_delay_ms=batch_max_delay_ms,
        )

        logger.info(
            "classifier: ready model=%s type=%s device=%s backend=%s batch=%s/%s",
            model_path,
            self._model_info.model_type,
            self.device,
            self._backend.__class__.__name__,
            batch_max_size,
            batch_max_delay_ms,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _configure_gpu_limit(self) -> None:
        if not self.device.startswith("cuda"):
            return
        if self._gpu_memory_frac is None:
            return
        if not hasattr(torch.cuda, "set_per_process_memory_fraction"):
            logger.warning(
                "classifier: torch build missing set_per_process_memory_fraction; skipping TOOL_GPU_FRAC"
            )
            return
        try:
            fraction = float(self._gpu_memory_frac)
        except (TypeError, ValueError):
            logger.warning("classifier: invalid TOOL_GPU_FRAC value %r; expected float", self._gpu_memory_frac)
            return
        if not (0.0 < fraction <= 1.0):
            logger.warning("classifier: TOOL_GPU_FRAC %.3f out of range (0,1]; ignoring", fraction)
            return
        fraction = max(0.01, min(fraction, 0.90))
        try:
            torch_device = torch.device(self.device)
        except Exception:
            torch_device = torch.device("cuda")
        device_index = torch_device.index
        if device_index is None:
            device_index = torch.cuda.current_device()
        if device_index in self._memory_fraction_configured:
            return
        try:
            torch.cuda.set_per_process_memory_fraction(fraction, device_index)
            self._memory_fraction_configured.add(device_index)
            logger.info(
                "classifier: reserved %.1f%% of cuda:%s for tool model (TOOL_GPU_FRAC)",
                fraction * 100.0,
                device_index,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("classifier: failed to honor TOOL_GPU_FRAC=%.3f (%s)", fraction, exc)

    def _format_input(self, user_utt: str, user_history: str = "") -> str:
        history = (user_history or "").strip()
        lines: list[str] = []
        if history:
            lines.append(history)
        current = user_utt.strip()
        if current and not current.upper().startswith("USER:"):
            current = f"USER: {current}"
        elif not current:
            current = "USER:"
        lines.append(current)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def classify(self, user_utt: str, user_history: str = "") -> tuple[bool, float]:
        """Return (should_take_screenshot, probability)."""
        text = self._format_input(user_utt, user_history)
        probs = self._batch.classify(text, timeout_s=self.request_timeout_s)

        if len(probs) < 2:
            p_yes = float(probs[-1])
        else:
            p_yes = float(probs[1])

        should_take = p_yes >= self.threshold
        return should_take, p_yes

    def run_tool_inference(self, user_utt: str, user_history: str = "") -> str:
        should_take, p_yes = self.classify(user_utt, user_history)
        logger.debug(
            "classifier: result=%s prob=%.3f user=%r",
            should_take,
            p_yes,
            user_utt[:80],
        )
        if should_take:
            return '[{"name": "take_screenshot"}]'
        return "[]"


__all__ = ["ClassifierToolAdapter"]
