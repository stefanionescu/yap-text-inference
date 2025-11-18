from __future__ import annotations

import json
import statistics as stats
from pathlib import Path
from typing import Any


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    k = max(0, min(len(values) - 1, int(round(q * (len(values) - 1)))))
    return sorted(values)[k]


def summarize_bench(title: str, results: list[dict[str, float]]) -> None:
    if not results:
        print(f"{title}: no results")
        return
    wall = [r.get("wall_s", 0.0) for r in results]
    audio = [r.get("audio_s", 0.0) for r in results]
    rtf = [r.get("rtf", 0.0) for r in results]
    xrt = [r.get("xrt", 0.0) for r in results]
    ttfb_e2e = [r.get("ttfb_e2e_s", 0.0) for r in results if r.get("ttfb_e2e_s", 0.0) > 0]
    ttfb_srv = [r.get("ttfb_server_s", 0.0) for r in results if r.get("ttfb_server_s", 0.0) > 0]
    lead_ms = [r.get("leading_silence_ms", 0.0) for r in results if r.get("leading_silence_ms") is not None]

    print(f"\n== {title} ==")
    print(f"n={len(results)}")
    print(f"Wall s      | avg={stats.mean(wall):.4f}  p50={stats.median(wall):.4f}  p95={_percentile(wall,0.95):.4f}")
    if ttfb_e2e:
        print(
            "TTFB (e2e)  | "
            f"avg={stats.mean(ttfb_e2e):.4f}  "
            f"p50={stats.median(ttfb_e2e):.4f}  "
            f"p95={_percentile(ttfb_e2e,0.95):.4f}"
        )
    if ttfb_srv:
        print(
            "TTFB (srv)  | "
            f"avg={stats.mean(ttfb_srv):.4f}  "
            f"p50={stats.median(ttfb_srv):.4f}  "
            f"p95={_percentile(ttfb_srv,0.95):.4f}"
        )
    if lead_ms:
        print(
            "Lead silence| "
            f"avg={stats.mean(lead_ms):.1f}ms  "
            f"p50={stats.median(lead_ms):.1f}ms  "
            f"p90={_percentile(lead_ms,0.90):.1f}ms  "
            f"p95={_percentile(lead_ms,0.95):.1f}ms"
        )
    print(f"Audio s     | avg={stats.mean(audio):.4f}")
    print(f"RTF         | avg={stats.mean(rtf):.4f}  p50={stats.median(rtf):.4f}  p95={_percentile(rtf,0.95):.4f}")
    print(f"xRT         | avg={stats.mean(xrt):.4f}")
    print(f"Throughput  | avg={stats.mean([r.get('throughput_min_per_min',0.0) for r in results]):.2f} min/min")


def report_sentence_mismatch(label: str, expected: list[str], received: list[str]) -> None:
    print(f"{label} ERROR: Sentence announcements mismatch.")
    print(f"Expected ({len(expected)}): {expected}")
    print(f"Received ({len(received)}): {received}")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in rows:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Saved per-session metrics to {path}")
    except Exception as e:
        print(f"Warning: could not write metrics JSONL: {e}")


def print_client_result(metrics: dict[str, Any], header: str | None = None) -> None:
    if header:
        print(header)
    server = metrics.get("server")
    voice = metrics.get("voice")
    outfile = metrics.get("outfile")
    text = metrics.get("text")
    if server is not None:
        print(f"Server: {server}")
    if voice is not None:
        print(f"Voice:  {voice}")
    if outfile:
        print(f"Out:    {outfile}")
    if text is not None:
        print(f"Text: '{text}'")

    print("\n== Result ==")
    ttfb_e2e = metrics.get("ttfb_e2e_s")
    ttfb_srv = metrics.get("ttfb_server_s")
    wall = metrics.get("wall_s")
    audio = metrics.get("audio_s")
    rtf = metrics.get("rtf")
    xrt = metrics.get("xrt")
    connect_ms = metrics.get("connect_ms")
    lead_ms = metrics.get("leading_silence_ms")

    if ttfb_e2e is not None:
        print(f"TTFB (e2e): {float(ttfb_e2e):.3f}s")
    if ttfb_srv is not None:
        print(f"TTFB (srv): {float(ttfb_srv):.3f}s")
    if wall is not None:
        print(f"Wall:  {float(wall):.3f}s")
    if audio is not None:
        print(f"Audio: {float(audio):.3f}s")
    if lead_ms is not None:
        print(f"Lead silence: {float(lead_ms):.1f}ms")
    if rtf is not None:
        print(f"RTF: {float(rtf):.3f}")
    if xrt is not None:
        print(f"xRT: {float(xrt):.3f}")
    if connect_ms is not None:
        print(f"Connect: {float(connect_ms):.1f}ms")
