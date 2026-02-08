"""Engine-related dataclasses."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass


@dataclass(slots=True)
class EngineOutput:
    """Unified output format for streaming generation."""

    text: str
    token_ids: list[int] | None = None
    finished: bool = False

    @classmethod
    def from_vllm(cls, output: Any) -> EngineOutput:
        if not getattr(output, "outputs", None):
            return cls(text="", finished=False)
        out = output.outputs[0]
        return cls(
            text=out.text if hasattr(out, "text") else "",
            token_ids=list(out.token_ids) if hasattr(out, "token_ids") else None,
            finished=out.finished if hasattr(out, "finished") else False,
        )

    @classmethod
    def from_trt(cls, chunk: Any, prev_text: str = "") -> EngineOutput:
        if not getattr(chunk, "outputs", None):
            return cls(text=prev_text, finished=False)
        out = chunk.outputs[0]
        text = getattr(out, "text", None) or prev_text
        token_ids = getattr(out, "token_ids", None) or getattr(out, "output_token_ids", None)
        finished = getattr(out, "finished", False)
        return cls(
            text=text,
            token_ids=list(token_ids) if token_ids else None,
            finished=finished,
        )


__all__ = ["EngineOutput"]
