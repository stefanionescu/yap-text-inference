from __future__ import annotations

import os
from typing import Any


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


def print_report(url: str, requests: int, concurrency: int, results: list[dict[str, Any]]) -> None:
    ok = [r for r in results if r.get("ok")]
    errs = [r for r in results if not r.get("ok")]
    tool_ttfb = [r["ttfb_toolcall_ms"] for r in ok if r.get("ttfb_toolcall_ms") is not None]
    chat_ttfb = [r["ttfb_chat_ms"] for r in ok if r.get("ttfb_chat_ms") is not None]
    first_sentence = [r["first_sentence_ms"] for r in ok if r.get("first_sentence_ms") is not None]
    first_3_words = [r["first_3_words_ms"] for r in ok if r.get("first_3_words_ms") is not None]

    print(f"url={url} total={requests} conc={concurrency} ok={len(ok)} err={len(errs)}")
    if tool_ttfb:
        p50 = percentile(tool_ttfb, 0.5)
        p95 = percentile(tool_ttfb, 0.95, minus_one=True)
        print(f"toolcall_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if chat_ttfb:
        p50 = percentile(chat_ttfb, 0.5)
        p95 = percentile(chat_ttfb, 0.95, minus_one=True)
        print(f"chat_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if first_sentence:
        p50 = percentile(first_sentence, 0.5)
        p95 = percentile(first_sentence, 0.95, minus_one=True)
        print(f"first_sentence_ms p50={p50:.1f} p95={p95:.1f}")
    if first_3_words:
        p50 = percentile(first_3_words, 0.5)
        p95 = percentile(first_3_words, 0.95, minus_one=True)
        print(f"first_3_words_ms p50={p50:.1f} p95={p95:.1f}")

    if errs:
        e = errs[0]
        emsg = e.get("error", "unknown error")
        print(f"example_error={emsg}")

        if "authentication_failed" in emsg:
            api_key = os.getenv("TEXT_API_KEY")
            if api_key:
                print(f"hint: Check TEXT_API_KEY environment variable (currently: '{api_key}')")
            else:
                print("hint: TEXT_API_KEY environment variable is required and must be set")
        elif "server_at_capacity" in emsg:
            print("hint: Server at capacity. Reduce concurrency (-c) or try again later.")

        capacity_errors = [err for err in errs if _is_capacity_error(err.get("error"))]
        if capacity_errors:
            limit_env = os.getenv("MAX_CONCURRENT_CONNECTIONS")
            limit_hint = f" (MAX_CONCURRENT_CONNECTIONS={limit_env})" if limit_env else ""
            print(f"capacity_rejections={len(capacity_errors)}{limit_hint}")
            print(
                "Observation: The server refused extra sessions once concurrency hit its limit. "
                "Lower --concurrency or add capacity if this is unexpected."
            )


