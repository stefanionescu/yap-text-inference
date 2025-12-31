from __future__ import annotations

import os
from typing import Any
from collections.abc import Iterable


# ============================================================================
# Internal Helpers
# ============================================================================


def percentile(values: list[float], frac: float, minus_one: bool = False) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    n = len(vals)
    idx = int(frac * n)
    if minus_one:
        idx = max(idx - 1, 0)
    if idx >= n:
        idx = n - 1
    return vals[idx]


def _is_capacity_error(message: str | None) -> bool:
    if not message:
        return False
    msg = message.lower()
    return "server_at_capacity" in msg or "1013" in msg


def _format_error_line(raw_error: str, all_errors: list[dict[str, Any]]) -> str:
    message = raw_error or "unknown error"
    normalized = message.lower()

    if "authentication_failed" in normalized:
        api_key = os.getenv("TEXT_API_KEY")
        if api_key:
            return "authentication_failed - provided TEXT_API_KEY was rejected"
        return "authentication_failed - TEXT_API_KEY environment variable is missing"

    if "server_at_capacity" in normalized:
        capacity_errors = [err for err in all_errors if _is_capacity_error(err.get("error"))]
        details: list[str] = []
        if capacity_errors:
            details.append(f"capacity_rejections={len(capacity_errors)}")
        limit_env = os.getenv("MAX_CONCURRENT_CONNECTIONS")
        if limit_env:
            details.append(f"MAX_CONCURRENT_CONNECTIONS={limit_env}")
        suffix = f" ({', '.join(details)})" if details else ""
        return f"server_at_capacity. Details: {suffix}"

    return message


def _print_latency_section(ok_results: Iterable[dict[str, Any]], prefix: str = "") -> None:
    ok_list = list(ok_results)
    tool_ttfb = [r["ttfb_toolcall_ms"] for r in ok_list if r.get("ttfb_toolcall_ms") is not None]
    chat_ttfb = [r["ttfb_chat_ms"] for r in ok_list if r.get("ttfb_chat_ms") is not None]
    first_sentence = [r["first_sentence_ms"] for r in ok_list if r.get("first_sentence_ms") is not None]
    first_3_words = [r["first_3_words_ms"] for r in ok_list if r.get("first_3_words_ms") is not None]

    if tool_ttfb:
        p50 = percentile(tool_ttfb, 0.5)
        p95 = percentile(tool_ttfb, 0.95, minus_one=True)
        print(f"{prefix}toolcall_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if chat_ttfb:
        p50 = percentile(chat_ttfb, 0.5)
        p95 = percentile(chat_ttfb, 0.95, minus_one=True)
        print(f"{prefix}chat_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if first_sentence:
        p50 = percentile(first_sentence, 0.5)
        p95 = percentile(first_sentence, 0.95, minus_one=True)
        print(f"{prefix}first_sentence_ms p50={p50:.1f} p95={p95:.1f}")
    if first_3_words:
        p50 = percentile(first_3_words, 0.5)
        p95 = percentile(first_3_words, 0.95, minus_one=True)
        print(f"{prefix}first_3_words_ms p50={p50:.1f} p95={p95:.1f}")


def _print_tagged_section(tag: str, results: list[dict[str, Any]]) -> None:
    ok = [r for r in results if r.get("ok")]
    if not ok:
        return
    prefix = f"[{tag}] "
    _print_latency_section(ok, prefix=prefix)


# ============================================================================
# Public API
# ============================================================================


def print_report(
    url: str,
    requests: int,
    concurrency: int,
    results: list[dict[str, Any]],
    *,
    double_ttfb: bool = False,
) -> None:
    ok = [r for r in results if r.get("ok")]
    errs = [r for r in results if not r.get("ok")]
    total_transactions = len(results)

    if not double_ttfb:
        print(f"url={url} total={requests} conc={concurrency} ok={len(ok)} err={len(errs)}")
        _print_latency_section(ok)
    else:
        print(
            f"url={url} connections={requests} transactions={total_transactions} "
            f"conc={concurrency} ok={len(ok)} err={len(errs)}"
        )
        _print_tagged_section("first", [r for r in results if r.get("phase") == 1])
        _print_tagged_section("second", [r for r in results if r.get("phase") == 2])

    if errs:
        emsg = str(errs[0].get("error", "unknown error"))
        print(f"ERROR: {_format_error_line(emsg, errs)}")


__all__ = ["print_report", "percentile"]
