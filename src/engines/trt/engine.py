"""TensorRT-LLM engine wrapper implementing BaseEngine interface.

This module provides the TRTEngine class that wraps TensorRT-LLM for inference.
Unlike vLLM, TRT-LLM uses pre-built engines and does not need periodic cache
resets due to its built-in KV cache block reuse mechanism.

Key Differences from vLLM:
    1. No JIT compilation - engines must be pre-built
    2. No cache reset support - block reuse handles memory
    3. No request priority support
    4. Abort is best-effort (iterator abandonment)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from collections.abc import AsyncGenerator

if TYPE_CHECKING:
    from tensorrt_llm.executor import GenerationResult
else:
    GenerationResult = Any  # Actual import happens lazily inside SuppressedFDContext

from ...telemetry.sentry import capture_error
from ...telemetry.instruments import get_metrics
from ..base import BaseEngine, EngineOutput, EngineNotReadyError

logger = logging.getLogger(__name__)


class TRTEngine(BaseEngine):
    """TensorRT-LLM based inference engine.

    TRT-LLM engines are pre-built and loaded from a directory containing
    the compiled TensorRT engine files (e.g., rank0.engine).

    Key differences from vLLM:
    - No periodic cache reset needed (block reuse is built-in)
    - Engine is pre-compiled, not JIT compiled
    - Uses different SamplingParams class
    """

    def __init__(self, llm: Any, tokenizer_id: str):
        """Initialize TRT engine wrapper.

        Args:
            llm: The tensorrt_llm LLM instance.
            tokenizer_id: HuggingFace model ID for the tokenizer.
        """
        self._llm = llm
        self._tokenizer_id = tokenizer_id
        self._shutdown = False
        self._executor = getattr(llm, "_executor", None)
        self._inflight: dict[str, GenerationResult] = {}

    @property
    def raw_engine(self) -> Any:
        """Access the underlying TRT-LLM engine."""
        return self._llm

    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation using TRT-LLM's generate_async API.

        Note: TRT-LLM doesn't support request prioritization like vLLM.
        """
        if self._shutdown:
            raise EngineNotReadyError("Engine has been shutdown")

        prev_text = ""
        generation = self._llm.generate_async(
            prompt,
            sampling_params,
            streaming=True,
        )

        trt_request_id = getattr(generation, "request_id", None)
        if isinstance(request_id, str) and trt_request_id is not None:
            self._inflight[request_id] = generation

        try:
            async for chunk in generation:
                output = EngineOutput.from_trt(chunk, prev_text)
                if output.text:
                    prev_text = output.text
                yield output
        finally:
            if isinstance(request_id, str):
                self._inflight.pop(request_id, None)

    async def abort(self, request_id: str) -> None:
        """Abort a TRT-LLM generation request.

        Note: TRT-LLM's abort mechanism may differ from vLLM.
        This is a best-effort implementation.
        """
        if not request_id:
            return

        pending = self._inflight.pop(request_id, None)
        trt_request_id = getattr(pending, "request_id", None)
        if trt_request_id is None:
            return

        executor = getattr(self._llm, "_executor", self._executor)
        if executor is None:
            get_metrics().errors_total.add(1, {"error.type": "executor_unavailable"})
            logger.warning("TRT-LLM: executor not available for cancellation")
            return

        try:
            executor.abort_request(int(trt_request_id))
            logger.info("TRT-LLM: cancelled request_id=%s", request_id)
        except Exception as exc:  # noqa: BLE001 - best effort abort
            capture_error(exc)
            get_metrics().errors_total.add(1, {"error.type": "trt_abort_failed"})
            logger.warning("TRT-LLM: failed to cancel request_id=%s", request_id, exc_info=True)

    async def shutdown(self) -> None:
        """Shutdown the TRT-LLM engine."""
        self._shutdown = True
        # TRT-LLM cleanup is handled by Python garbage collection
        # No explicit shutdown method like vLLM's AsyncLLMEngine
        logger.info("TRT-LLM: engine shutdown complete")

    @property
    def supports_cache_reset(self) -> bool:
        """TRT-LLM does not need periodic cache reset.

        The KV cache uses block reuse which handles memory management
        automatically without fragmentation issues.
        """
        return False

    async def reset_caches(self, reason: str) -> bool:
        """No-op for TRT-LLM - cache reset not needed."""
        logger.debug("TRT-LLM: cache reset requested (reason=%s) but not supported", reason)
        return False


__all__ = ["TRTEngine"]
