from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


def _percentile(samples: Sequence[float], frac: float) -> float:
    if not samples:
        raise ValueError("percentile requires at least one sample")
    if frac <= 0:
        return min(samples)
    if frac >= 1:
        return max(samples)
    ordered = sorted(samples)
    position = frac * (len(ordered) - 1)
    lower_idx = math.floor(position)
    upper_idx = math.ceil(position)
    if lower_idx == upper_idx:
        return ordered[lower_idx]
    weight = position - lower_idx
    return ordered[lower_idx] + (ordered[upper_idx] - ordered[lower_idx]) * weight


def _coerce(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


@dataclass
class TTFBAggregator:
    """Accumulates tool/chat TTFB samples and prints summary statistics."""

    tool_samples: list[float] = field(default_factory=list)
    chat_samples: list[float] = field(default_factory=list)

    def record(self, metrics: Mapping[str, Any]) -> None:
        tool = _coerce(metrics.get("ttfb_toolcall_ms"))
        chat = _coerce(metrics.get("ttfb_chat_ms"))
        if tool is not None:
            self.tool_samples.append(tool)
        if chat is not None:
            self.chat_samples.append(chat)

    def has_samples(self) -> bool:
        return bool(self.tool_samples or self.chat_samples)

    def emit(self, sink: Callable[[str], None], *, label: str = "TTFB") -> None:
        for kind, samples in (("TOOL", self.tool_samples), ("CHAT", self.chat_samples)):
            if not samples:
                continue
            stats = _build_stats(samples)
            sink(
                (
                    f"{label} [{kind}] "
                    f"first={stats['first']:.2f} "
                    f"avg={stats['average']:.2f} "
                    f"p50={stats['p50']:.2f} "
                    f"p90={stats['p90']:.2f} "
                    f"p95={stats['p95']:.2f} "
                    f"samples={stats['count']}"
                )
            )


def _build_stats(samples: Sequence[float]) -> dict[str, float | int]:
    count = len(samples)
    return {
        "count": count,
        "first": samples[0],
        "average": sum(samples) / count,
        "p50": _percentile(samples, 0.50),
        "p90": _percentile(samples, 0.90),
        "p95": _percentile(samples, 0.95),
    }


__all__ = ["TTFBAggregator"]
