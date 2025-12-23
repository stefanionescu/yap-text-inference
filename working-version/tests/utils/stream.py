from __future__ import annotations

import asyncio
import contextlib
import json
import time

from websockets.exceptions import ConnectionClosed


async def recv_pcm_and_sentences(
    ws,
) -> tuple[bytes, list[str], float | None]:
    first_chunk_at: float | None = None
    total: bytearray = bytearray()
    sentences: list[str] = []

    while True:
        try:
            msg = await ws.recv()
        except asyncio.TimeoutError:
            break
        except ConnectionClosed:
            break

        if isinstance(msg, bytes | bytearray):
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()
            total.extend(msg)
        elif isinstance(msg, str):
            with contextlib.suppress(Exception):
                obj = json.loads(msg)
                if isinstance(obj, dict):
                    t = str(obj.get("type", "")).lower()
                    if t == "sentence":
                        s = str(obj.get("text", "")).strip()
                        if s:
                            sentences.append(s)
                    elif t == "audio_end":
                        break
                    elif t == "sentence_end":
                        # boundary signal; caller doesn't need per-sentence PCM segmentation here
                        pass

    return bytes(total), sentences, first_chunk_at
