"""Batched classifier adapter for screenshot intent detection.

This module provides the high-level ClassifierToolAdapter that:

1. Manages the classification backend lifecycle
2. Formats inputs (history + current utterance)
3. Applies decision thresholds
4. Enforces GPU memory limits
5. Coordinates micro-batching for efficiency

The adapter is the main entry point for tool/screenshot classification.
"""

from __future__ import annotations

import json
import logging

import torch  # type: ignore[import]

from src.state import ClassifierModelInfo
from src.config.tool import (
    TOOL_MAX_GPU_FRAC,
    TOOL_MIN_GPU_FRAC,
    TOOL_MIN_TIMEOUT_S,
    TOOL_NEGATIVE_RESULT,
    TOOL_POSITIVE_RESULT,
    TOOL_POSITIVE_LABEL_INDEX,
)

from .batch import BatchExecutor
from .backend import TorchClassifierBackend
from .info import build_model_info, resolve_history_token_limit

logger = logging.getLogger(__name__)

_POSITIVE_JSON = json.dumps(TOOL_POSITIVE_RESULT)
_NEGATIVE_JSON = json.dumps(TOOL_NEGATIVE_RESULT)


class ClassifierToolAdapter:
    """Microbatched classifier adapter for screenshot intent detection.

    This class coordinates between:
    - The PyTorch inference backend (TorchClassifierBackend)
    - The batching layer (BatchExecutor)
    - GPU memory management
    - Threshold-based decision making

    Attributes:
        model_path: Path or HuggingFace ID of the classifier model.
        threshold: Probability threshold for "take screenshot" decision.
        device: CUDA device string (e.g., "cuda:0") or "cpu".
        dtype: Torch dtype (float16 for GPU, float32 for CPU).
        request_timeout_s: Maximum wait time for batch results.
    """

    def __init__(
        self,
        model_path: str,
        *,
        threshold: float = 0.66,
        device: str | None = None,
        compile_model: bool = True,
        max_length: int | None = None,
        history_max_tokens: int | None = None,
        batch_max_size: int = 3,
        batch_max_delay_ms: float = 10.0,
        request_timeout_s: float = 5.0,
        gpu_memory_frac: float | None = None,
    ) -> None:
        """Initialize the classifier adapter.

        Args:
            model_path: HuggingFace model path or local directory.
            threshold: Probability threshold for positive classification.
            device: Target device (defaults to cuda if available).
            compile_model: Whether to use torch.compile() for optimization.
            max_length: Optional total input sequence length override.
            history_max_tokens: Optional history token budget override.
            batch_max_size: Maximum requests per micro-batch.
            batch_max_delay_ms: Maximum wait time to fill a batch.
            request_timeout_s: Per-request timeout for classification.
            gpu_memory_frac: Fraction of GPU memory to reserve (0-1).
        """
        self.model_path = model_path
        self.threshold = threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self.request_timeout_s = max(TOOL_MIN_TIMEOUT_S, float(request_timeout_s))
        self._gpu_memory_frac = gpu_memory_frac
        self._memory_fraction_configured: set[int] = set()

        self._configure_gpu_limit()
        self._model_info: ClassifierModelInfo = build_model_info(model_path, max_length)
        resolved_history_tokens = resolve_history_token_limit(
            max_length=self._model_info.max_length,
            history_tokens=history_max_tokens,
        )
        self._backend = TorchClassifierBackend(
            self._model_info,
            device=self.device,
            dtype=self.dtype,
            compile_model=compile_model,
        )
        # Clamp history budget to the backend's effective tokenizer/model max length.
        self.max_history_tokens = min(resolved_history_tokens, self._backend.max_length)
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
        logger.info(
            "classifier: token limits model=%s config_max_length=%s backend_max_length=%s history_tokens=%s",
            model_path,
            self._model_info.max_length,
            self._backend.max_length,
            self.max_history_tokens,
        )

    # ============================================================================
    # Internal helpers
    # ============================================================================
    def _get_device_index(self) -> int:
        """Get CUDA device index from device string."""
        try:
            idx = torch.device(self.device).index
            return idx if idx is not None else torch.cuda.current_device()
        except Exception:
            return torch.cuda.current_device()

    def _configure_gpu_limit(self) -> None:
        """Configure GPU memory limit for the classifier."""
        if not self.device.startswith("cuda") or self._gpu_memory_frac is None:
            return

        device_index = self._get_device_index()
        if device_index in self._memory_fraction_configured:
            return

        fraction = max(TOOL_MIN_GPU_FRAC, min(self._gpu_memory_frac, TOOL_MAX_GPU_FRAC))
        try:
            torch.cuda.set_per_process_memory_fraction(fraction, device_index)
            self._memory_fraction_configured.add(device_index)
            logger.info("classifier: reserved %.1f%% of cuda:%s", fraction * 100.0, device_index)
        except Exception as exc:  # noqa: BLE001
            logger.warning("classifier: failed to set GPU memory fraction: %s", exc)

    def _format_input(self, user_utt: str, user_history: str = "") -> str:
        """Combine history and current utterance into classifier input."""
        parts = [p for p in [(user_history or "").strip(), user_utt.strip()] if p]
        return "\n".join(parts)

    # ============================================================================
    # Public API
    # ============================================================================
    def classify(self, user_utt: str, user_history: str = "") -> tuple[bool, float]:
        """Classify whether a screenshot should be taken.

        Args:
            user_utt: Current user utterance to classify.
            user_history: Previous user messages for context.

        Returns:
            Tuple of (should_take_screenshot, probability):
            - should_take_screenshot: True if probability >= threshold
            - probability: Raw model probability for "take screenshot"
        """
        text = self._format_input(user_utt, user_history)
        probs = self._batch.classify(text, timeout_s=self.request_timeout_s)

        # Binary classification: index 1 is the positive class probability
        p_yes = float(probs[TOOL_POSITIVE_LABEL_INDEX])
        should_take = p_yes >= self.threshold
        return should_take, p_yes

    def run_tool_inference(self, user_utt: str, user_history: str = "") -> str:
        """Run tool inference and return a JSON result string.

        This is the main entry point for the tool execution pipeline.

        Args:
            user_utt: Current user utterance.
            user_history: Previous user messages for context.

        Returns:
            JSON string: '[{"name": "take_screenshot"}]' if positive,
            or '[]' if negative.
        """
        should_take, p_yes = self.classify(user_utt, user_history)
        logger.debug(
            "classifier: result=%s prob=%.3f user=%r",
            should_take,
            p_yes,
            user_utt[:80],
        )
        return _POSITIVE_JSON if should_take else _NEGATIVE_JSON


__all__ = ["ClassifierToolAdapter"]
