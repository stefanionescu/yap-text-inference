#!/usr/bin/env python3
"""
Concurrent benchmark for the WebSocket /ws endpoint.

Runs N total sessions with up to M concurrent connections. For each request,
records:
- ttfb_toolcall_ms: time to receive toolcall decision
- ttfb_chat_ms: time to first chat token (if chat happens)
- first_sentence_ms: time to first complete sentence (if chat happens)
- first_3_words_ms: time to first three words (if chat happens)

Prints p50/p95 for each metric across completed requests. No intermediate logs.

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- YAP_TEXT_API_KEY: API key for authentication (default: yap_token)
- ASSISTANT_GENDER: female|male (default: female)
- PERSONA_STYLE: persona style (default: flirty)

Note: API key authentication is required. The client will automatically
append the API key as a query parameter to all WebSocket connections.
"""

from __future__ import annotations

import argparse
import asyncio
import os


_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"”')\]]+)?(?:\s|$)")


def _contains_complete_sentence(text: str) -> bool:
    return _SENTENCE_END_RE.search(text) is not None


def _has_at_least_n_words(text: str, n: int) -> bool:
    # Whitespace-delimited token count; counts punctuation-attached tokens as words
    return len(text.strip().split()) >= n


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Yap Text Inference WS server")
    p.add_argument("message", nargs="*", help="optional user message for all requests")
    p.add_argument("--requests", "-n", type=int, default=16, help="total number of requests")
    p.add_argument("--concurrency", "-c", type=int, default=8, help="max in-flight requests")
    p.add_argument("--timeout", type=float, default=120.0, help="per-request total timeout (s)")
    p.add_argument(
        "--url",
        default=os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws"),
        help="WebSocket URL (default env SERVER_WS_URL or ws://127.0.0.1:8000/ws)",
    )
    p.add_argument(
        "--assistant-gender",
        "--gender",
        "-g",
        dest="assistant_gender",
        choices=["female", "male", "woman", "man"],
        default=os.getenv("ASSISTANT_GENDER", "female"),
        help="assistant gender (normalized by server)",
    )
    p.add_argument(
        "--persona-style",
        "--style",
        "-s",
        dest="persona_style",
        default=os.getenv("PERSONA_STYLE", "flirty"),
        help="persona style (e.g., wholesome, savage, flirty)",
    )
    return p.parse_args()


def main() -> None:
    """Thin orchestrator: parse CLI args and run the benchmark."""
    from benchmark.runner import run_benchmark

    args = _parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()


