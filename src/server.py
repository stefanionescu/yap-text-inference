from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse

from vllm.sampling_params import SamplingParams

from .config import (
    CHAT_MAX_OUT,
    HISTORY_MAX_TOKENS,
    USER_UTT_MAX_TOKENS,
    STREAM_RATE_TOKS_PER_S,
    TOOL_MAX_OUT,
    TEXTPROC_ENABLE,
)
from .engines import get_chat_engine, get_tool_engine
from .persona import build_chat_prompt, build_hammer_prompt, compose_persona
from .textproc import StreamCleaner, ensure_proper_ending_punctuation
from .tokens import approx_token_count, trim_text_to_token_limit
from .config import EXACT_TOKEN_TRIM
if EXACT_TOKEN_TRIM:
    from .tokenizer_utils import exact_token_count as token_count_exact
    from .tokenizer_utils import trim_text_to_token_limit_exact as trim_text_exact


app = FastAPI(default_response_class=ORJSONResponse)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.on_event("startup")
async def _warm():
    # Warm both engines to shave first-turn TTFT
    from vllm.sampling_params import SamplingParams
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["\n", "</s>"])

    # Warm chat engine (minimal persona-only prompt) first
    rid_c = f"warm-chat-{uuid.uuid4()}"
    stream_c = get_chat_engine().generate(
        prompt="<|persona|>\nWARM\n<|assistant|>\n",
        sampling_params=params,
        request_id=rid_c,
        priority=0.9,
        use_prefix_cache=True,
    )
    async for _ in stream_c:
        break

    # Then warm tool engine
    rid_t = f"warm-tool-{uuid.uuid4()}"
    stream_t = get_tool_engine().generate(
        prompt="warmup",
        sampling_params=params,
        request_id=rid_t,
        priority=0.9,
        use_prefix_cache=True,
    )
    async for _ in stream_t:
        break


# Track active session tasks/requests
session_tasks: Dict[str, asyncio.Task] = {}
session_active_req: Dict[str, str] = {}


async def run_toolcall(session_id: str, user_utt: str, request_id: Optional[str] = None):
    req_id = request_id or f"tool-{uuid.uuid4()}"
    session_active_req[session_id] = req_id

    params = SamplingParams(
        temperature=0.0,
        top_p=0.0,
        top_k=1,
        max_tokens=TOOL_MAX_OUT,
        stop=["\n", "</s>"]
    )

    stream = get_tool_engine().generate(
        prompt=build_hammer_prompt(user_utt),
        sampling_params=params,
        request_id=req_id,
        priority=1.0,
    )

    pieces = []
    async for out in stream:
        if session_active_req.get(session_id) != req_id:
            await get_tool_engine().abort_request(req_id)
            return {"cancelled": True}
        if out.outputs:
            pieces.append(out.outputs[0].text)

    text = "".join(pieces).strip()
    return {"cancelled": False, "text": text}


async def run_chat_stream(
    session_id: str,
    persona_text: str,
    history_text: str,
    user_utt: str,
    stream_rate: float,
    request_id: Optional[str] = None,
):
    req_id = request_id or f"chat-{uuid.uuid4()}"
    session_active_req[session_id] = req_id

    params = SamplingParams(
        temperature=0.7,
        top_p=0.9,
        top_k=-1,
        max_tokens=CHAT_MAX_OUT,
        stop=["<|end|>", "</s>"]
    )

    prompt = build_chat_prompt(persona_text, history_text, user_utt)
    stream = get_chat_engine().generate(
        prompt=prompt,
        sampling_params=params,
        request_id=req_id,
        priority=0.5,
    )

    min_interval = 1.0 / max(1e-6, stream_rate)
    last_emit = time.perf_counter()
    last_text = ""

    cleaner = StreamCleaner() if TEXTPROC_ENABLE else None

    async for out in stream:
        if session_active_req.get(session_id) != req_id:
            await get_chat_engine().abort_request(req_id)
            return

        if not out.outputs:
            continue

        full_text = out.outputs[0].text
        if cleaner is not None:
            full_text = cleaner.clean_increment(full_text)
        delta = full_text[len(last_text) :]
        if not delta:
            continue

        now = time.perf_counter()
        sleep_for = min_interval - (now - last_emit)
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)
        last_emit = time.perf_counter()
        last_text = full_text

        yield delta


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    session_id: Optional[str] = None

    try:
        while True:
            msg = json.loads(await ws.receive_text())

            if msg["type"] == "start":
                # Cancel previous
                if session_id and session_id in session_tasks:
                    session_active_req[session_id] = "CANCELLED"
                    session_tasks[session_id].cancel()

                session_id = msg["session_id"]

                # Persona resolution: raw persona_text or composed from style/gender
                persona_text = msg.get("persona_text")
                if not persona_text:
                    persona_text = compose_persona(
                        style=msg.get("persona_style", "wholesome"),
                        assistant_gender=msg.get("assistant_gender", "woman"),
                        user_identity=msg.get("user_identity", "non-binary"),
                    )

                history_text = msg.get("history_text", "")
                user_utt = msg["user_utterance"]
                # Trim user utterance to first USER_UTT_MAX_TOKENS
                if EXACT_TOKEN_TRIM:
                    user_utt = trim_text_exact(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
                else:
                    user_utt = trim_text_to_token_limit(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
                # Trim rolling history to HISTORY_MAX_TOKENS, keep most recent
                if EXACT_TOKEN_TRIM:
                    # Fast path: only tokenize if likely over the limit by approx check
                    if approx_token_count(history_text) > HISTORY_MAX_TOKENS:
                        # exact trim using end-keep
                        history_text = trim_text_exact(history_text, max_tokens=HISTORY_MAX_TOKENS, keep="end")
                else:
                    if approx_token_count(history_text) > HISTORY_MAX_TOKENS:
                        history_text = trim_text_to_token_limit(history_text, max_tokens=HISTORY_MAX_TOKENS, keep="end")
                rate = float(msg.get("stream_rate_toks_per_s", STREAM_RATE_TOKS_PER_S))

                # 1) Toolcall (fast)
                tc = await run_toolcall(session_id, user_utt)
                if tc.get("cancelled"):
                    await ws.send_text(json.dumps({"type": "done", "cancelled": True}))
                    continue

                raw = tc["text"].strip()
                is_tool = False
                if raw.startswith("["):
                    is_tool = raw != "[]"

                await ws.send_text(json.dumps({"type": "toolcall", "status": "yes" if is_tool else "no", "raw": raw}))
                if is_tool:
                    await ws.send_text(json.dumps({"type": "done", "usage": {}}))
                    continue

                # 2) Chat (stream)
                async def _run():
                    final_text = ""
                    async for chunk in run_chat_stream(
                        session_id, persona_text, history_text, user_utt, rate
                    ):
                        await ws.send_text(json.dumps({"type": "token", "text": chunk}))
                        final_text += chunk
                    if TEXTPROC_ENABLE:
                        punct_fixed = ensure_proper_ending_punctuation(final_text)
                        if punct_fixed != final_text:
                            extra = punct_fixed[len(final_text):]
                            if extra:
                                await ws.send_text(json.dumps({"type": "token", "text": extra}))
                    # Emit normalized final text so clients can append exact bytes
                    await ws.send_text(json.dumps({
                        "type": "final",
                        "normalized_text": punct_fixed if TEXTPROC_ENABLE else final_text
                    }))
                    await ws.send_text(json.dumps({"type": "done", "usage": {}}))

                task = asyncio.create_task(_run())
                session_tasks[session_id] = task

            elif msg["type"] == "cancel":
                if session_id:
                    session_active_req[session_id] = "CANCELLED"
                    t = session_tasks.get(session_id)
                    if t:
                        t.cancel()
                    rid = session_active_req.get(session_id, "")
                    try:
                        if rid:
                            await get_chat_engine().abort_request(rid)
                    except Exception:
                        pass
                    try:
                        if rid:
                            await get_tool_engine().abort_request(rid)
                    except Exception:
                        pass
                await ws.send_text(json.dumps({"type": "done", "cancelled": True}))

            elif msg["type"] == "warm_persona":
                # Accept explicit persona_text or compose
                persona_text = msg.get("persona_text")
                if not persona_text:
                    persona_text = compose_persona(
                        style=msg.get("persona_style", "wholesome"),
                        assistant_gender=msg.get("assistant_gender", "woman"),
                        user_identity=msg.get("user_identity", "non-binary"),
                    )
                warm_prompt = f"<|persona|>\n{persona_text.strip()}\n<|assistant|>\n"
                params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
                req_id = f"warm-p-{uuid.uuid4()}"
                stream = get_chat_engine().generate(
                    prompt=warm_prompt,
                    sampling_params=params,
                    request_id=req_id,
                    priority=0.6,
                )
                async for _ in stream:
                    break
                await ws.send_text(json.dumps({"type": "warmed", "segment": "persona", "bytes": len(persona_text)}))

            elif msg["type"] == "warm_history":
                history_text = msg.get("history_text", "")
                if EXACT_TOKEN_TRIM:
                    if approx_token_count(history_text) > HISTORY_MAX_TOKENS:
                        history_text = trim_text_exact(history_text, max_tokens=HISTORY_MAX_TOKENS, keep="end")
                else:
                    if approx_token_count(history_text) > HISTORY_MAX_TOKENS:
                        history_text = trim_text_to_token_limit(history_text, max_tokens=HISTORY_MAX_TOKENS, keep="end")
                warm_prompt = f"<|history|>\n{history_text.strip()}\n<|assistant|>\n"
                params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
                req_id = f"warm-h-{uuid.uuid4()}"
                stream = get_chat_engine().generate(
                    prompt=warm_prompt,
                    sampling_params=params,
                    request_id=req_id,
                    priority=0.6,
                )
                async for _ in stream:
                    break
                await ws.send_text(json.dumps({"type": "warmed", "segment": "history", "bytes": len(history_text)}))

            else:
                await ws.send_text(json.dumps({"type": "error", "message": "unknown msg type"}))

    except WebSocketDisconnect:
        if session_id:
            rid = session_active_req.get(session_id, "")
            session_active_req[session_id] = "CANCELLED"
            t = session_tasks.get(session_id)
            if t:
                t.cancel()
            try:
                if rid:
                    await get_chat_engine().abort_request(rid)
            except Exception:
                pass
            try:
                if rid:
                    await get_tool_engine().abort_request(rid)
            except Exception:
                pass
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))


