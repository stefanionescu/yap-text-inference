from __future__ import annotations

import asyncio
import random
import json
import time
import uuid
import os
from datetime import datetime
from typing import Dict, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse

from vllm.sampling_params import SamplingParams
from prompts import PERSONALITIES

from .config import (
    CHAT_MODEL,
    TOOL_MODEL,
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
from .config import STREAM_FLUSH_MS
if EXACT_TOKEN_TRIM:
    from .tokenizer_utils import exact_token_count as token_count_exact
    from .tokenizer_utils import trim_text_to_token_limit_exact as trim_text_exact

# --- Chat sampling defaults (as requested) ---
CHAT_TEMPERATURE = 0.55
CHAT_TOP_P = 0.90
CHAT_TOP_K = 60
CHAT_MIN_P = 0.05
CHAT_REPEAT_PENALTY = 1.10

# --- Extra STOP sequences for chat model ---
STOP = [" |", "  |", "<|im_end|>", "|im_end|>", " ‍♀️", " ‍♂️"]

# --- Toolcall sampling defaults ---
TOOL_TEMPERATURE = 0.05
TOOL_TOP_P = 1.0
TOOL_TOP_K = 1
TOOL_STOP = ["\n", "</s>"]

# Per-session metadata: fixed seed + timestamp string
session_meta: Dict[str, Dict[str, Any]] = {}

# Allowed personalities/styles (from prompts.py)
ALLOWED_PERSONALITIES = set(PERSONALITIES.keys())

# --- Gender normalization & validation ---
def _norm_gender(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = val.strip().lower()
    if v in ("woman", "female", "f", "w"):
        return "woman"
    if v in ("man", "male", "m"):
        return "man"
    return None

# Time classification util
def get_time_classification(hour: int) -> str:
    if hour == 0:
        return "Midnight"
    elif 1 <= hour <= 3:
        return "Night"
    elif 4 <= hour <= 6:
        return "Early Morning"
    elif 7 <= hour <= 11:
        return "Morning"
    elif hour == 12:
        return "Noon"
    elif 13 <= hour <= 16:
        return "Afternoon"
    elif 17 <= hour <= 20:
        return "Early Evening"
    elif 21 <= hour <= 23:
        return "Evening"
    return "Unknown"


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
        priority=1,
    )
    async for _ in stream_c:
        break

    # Then warm tool engine
    rid_t = f"warm-tool-{uuid.uuid4()}"
    stream_t = get_tool_engine().generate(
        prompt="warmup",
        sampling_params=params,
        request_id=rid_t,
        priority=1,
    )
    async for _ in stream_t:
        break


# Track active session tasks/requests
session_tasks: Dict[str, asyncio.Task] = {}
session_active_req: Dict[str, str] = {}
# Track in-flight tool req ids (when tool router runs in parallel with chat)
session_tool_req: Dict[str, str] = {}


async def run_toolcall(
    session_id: str,
    user_utt: str,
    request_id: Optional[str] = None,
    mark_active: bool = True,
):
    req_id = request_id or f"tool-{uuid.uuid4()}"
    if mark_active:
        session_active_req[session_id] = req_id

    params = SamplingParams(
        temperature=TOOL_TEMPERATURE,
        top_p=TOOL_TOP_P,
        top_k=TOOL_TOP_K,
        max_tokens=TOOL_MAX_OUT,
        stop=TOOL_STOP,
        seed=session_meta.get(session_id, {}).get("seed", 0),
    )

    stream = get_tool_engine().generate(
        prompt=build_hammer_prompt(user_utt),
        sampling_params=params,
        request_id=req_id,
        priority=1,
    )

    pieces = []
    TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "10"))

    async def _iter_tool():
        async for out in stream:
            yield out

    try:
        async with asyncio.timeout(TOOL_TIMEOUT_S):
            async for out in _iter_tool():
                if mark_active and session_active_req.get(session_id) != req_id:
                    await get_tool_engine().abort_request(req_id)
                    return {"cancelled": True}
                if out.outputs:
                    pieces.append(out.outputs[0].text)
    except asyncio.TimeoutError:
        try:
            await get_tool_engine().abort_request(req_id)
        except Exception:
            pass
        return {"cancelled": True}

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
        temperature=CHAT_TEMPERATURE,
        top_p=CHAT_TOP_P,
        top_k=CHAT_TOP_K,
        min_p=CHAT_MIN_P,
        repetition_penalty=CHAT_REPEAT_PENALTY,
        max_tokens=CHAT_MAX_OUT,
        stop=STOP + ["<|end|>", "</s>"],
        seed=session_meta.get(session_id, {}).get("seed", 0),
    )

    prompt = build_chat_prompt(persona_text, history_text, user_utt)
    stream = get_chat_engine().generate(
        prompt=prompt,
        sampling_params=params,
        request_id=req_id,
        priority=0,
    )

    # realtime mode: emit ASAP. optional micro-coalescer if STREAM_FLUSH_MS>0
    last_text = ""
    # robust env parsing; treat blank/None as 0
    env_flush = os.getenv("STREAM_FLUSH_MS", "")
    try:
        flush_ms = float(env_flush) if env_flush.strip() else float(STREAM_FLUSH_MS)
    except Exception:
        flush_ms = float(STREAM_FLUSH_MS)
    buf = []
    last_flush = time.perf_counter()

    cleaner = StreamCleaner() if TEXTPROC_ENABLE else None

    GEN_TIMEOUT_S = float(os.getenv("GEN_TIMEOUT_S", "30"))

    async def _iter_stream():
        async for out in stream:
            yield out

    try:
        async with asyncio.timeout(GEN_TIMEOUT_S):
            async for out in _iter_stream():
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

                last_text = full_text

                if flush_ms <= 0:
                    # pure realtime: send immediately
                    yield delta
                else:
                    buf.append(delta)
                    now = time.perf_counter()
                    if (now - last_flush) * 1000.0 >= flush_ms:
                        yield "".join(buf)
                        buf.clear()
                        last_flush = now
    except asyncio.TimeoutError:
        try:
            await get_chat_engine().abort_request(req_id)
        except Exception:
            pass
        return

    # flush any tail if coalescer was on
    if flush_ms > 0 and buf:
        yield "".join(buf)


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

                # Initialize per-session metadata (seed + timestamp) once
                if session_id not in session_meta:
                    SESSION_SEED = random.randint(1, 1_000_000)
                    now = datetime.now()
                    time_classification = get_time_classification(now.hour)
                    now_str = now.strftime(f"%d/%m/%Y %A %I:%M %p ({time_classification})")
                    session_meta[session_id] = {
                        "seed": SESSION_SEED,
                        "now_str": now_str,
                        # defaults that can be overridden on start
                        "assistant_gender": None,
                        "persona_style": "wholesome",
                        "persona_text_override": None,
                        # expose models (handy for client logs)
                        "chat_model": CHAT_MODEL,
                        "tool_model": TOOL_MODEL,
                    }

                # Pull fixed values for this session
                sess_seed = session_meta[session_id]["seed"]
                sess_now_str = session_meta[session_id]["now_str"]

                # --- REQUIRE assistant_gender & persona_style on start; allow override persona ---
                incoming_gender = _norm_gender(msg.get("assistant_gender"))
                if incoming_gender is None and session_meta[session_id].get("assistant_gender") is None:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": "assistant_gender is required on start: use 'female'/'male' (or 'woman'/'man')."
                    }))
                    continue
                if incoming_gender is not None:
                    session_meta[session_id]["assistant_gender"] = incoming_gender
                # Validate persona_style: required at start and must be allowed
                incoming_style = (msg.get("persona_style") or "").strip()
                if not session_meta[session_id].get("persona_text_override"):
                    if not incoming_style and session_meta[session_id].get("persona_style") is None:
                        await ws.send_text(json.dumps({
                            "type": "error",
                            "message": f"persona_style is required on start; allowed: {sorted(ALLOWED_PERSONALITIES)}"
                        }))
                        continue
                    if incoming_style:
                        if incoming_style not in ALLOWED_PERSONALITIES:
                            await ws.send_text(json.dumps({
                                "type": "error",
                                "message": f"invalid persona_style '{incoming_style}'; allowed: {sorted(ALLOWED_PERSONALITIES)}"
                            }))
                            continue
                        session_meta[session_id]["persona_style"] = incoming_style
                # Optional raw persona override for this session
                session_meta[session_id]["persona_text_override"] = msg.get("persona_text") or None

                # Persona resolution: raw persona_text or composed from style/gender
                if session_meta[session_id]["persona_text_override"]:
                    persona_text = session_meta[session_id]["persona_text_override"]
                else:
                    persona_text = compose_persona(
                        style=session_meta[session_id]["persona_style"],
                        assistant_gender=session_meta[session_id]["assistant_gender"] or "woman",
                        user_identity=msg.get("user_identity", "non-binary"),
                        now_str=sess_now_str,
                    )

                # -------- ACK: session start / (re)config pinned --------
                await ws.send_text(json.dumps({
                    "type": "ack",
                    "for": "start",
                    "ok": True,
                    "session_id": session_id,
                    "seed": sess_seed,
                    "now": sess_now_str,
                    "assistant_gender": session_meta[session_id]["assistant_gender"],
                    "persona_style": session_meta[session_id]["persona_style"],
                    "persona_text_override": bool(session_meta[session_id]["persona_text_override"]),
                    "models": {"chat": session_meta[session_id]["chat_model"],
                               "tool": session_meta[session_id]["tool_model"]}
                }))

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

                # 1) Start tool router and chat in parallel with buffer-then-flush
                async def _run_start():
                    TOOL_HARD_TIMEOUT_MS = float(os.getenv("TOOL_HARD_TIMEOUT_MS", "300"))
                    PREBUFFER_MAX_CHARS = int(os.getenv("PREBUFFER_MAX_CHARS", "8000"))

                    # Kick off tool router (do not mark active to avoid clobbering chat req id)
                    tool_req_id = f"tool-{uuid.uuid4()}"
                    session_tool_req[session_id] = tool_req_id
                    tool_task = asyncio.create_task(
                        run_toolcall(session_id, user_utt, request_id=tool_req_id, mark_active=False)
                    )

                    # Start chat stream immediately, but buffer locally until router decision
                    chat_req_id = f"chat-{uuid.uuid4()}"
                    session_active_req[session_id] = chat_req_id
                    chat_stream = run_chat_stream(
                        session_id, persona_text, history_text, user_utt, rate, request_id=chat_req_id
                    )

                    buffer = []
                    buffer_chars = 0
                    flushing = False
                    final_text = ""

                    async def chat_producer():
                        nonlocal flushing, final_text, buffer_chars
                        try:
                            async for chunk in chat_stream:
                                if session_active_req.get(session_id) != chat_req_id:
                                    break
                                if not flushing:
                                    buffer.append(chunk)
                                    buffer_chars += len(chunk)
                                    if PREBUFFER_MAX_CHARS > 0 and buffer_chars >= PREBUFFER_MAX_CHARS:
                                        flushing = True
                                        joined = "".join(buffer)
                                        if joined:
                                            await ws.send_text(json.dumps({"type": "token", "text": joined}))
                                            final_text += joined
                                            buffer.clear()
                                    continue
                                await ws.send_text(json.dumps({"type": "token", "text": chunk}))
                                final_text += chunk
                        except asyncio.CancelledError:
                            pass

                    producer_task = asyncio.create_task(chat_producer())

                    # Wait for tool router (capped by hard timeout unless set to -1)
                    tool_res = None
                    try:
                        if TOOL_HARD_TIMEOUT_MS < 0:
                            tool_res = await tool_task
                        else:
                            tool_res = await asyncio.wait_for(tool_task, timeout=TOOL_HARD_TIMEOUT_MS / 1000.0)
                    except asyncio.TimeoutError:
                        try:
                            tool_task.cancel()
                        except Exception:
                            pass
                        # best-effort abort underlying tool request
                        try:
                            if session_tool_req.get(session_id):
                                await get_tool_engine().abort_request(session_tool_req.get(session_id, ""))
                        except Exception:
                            pass
                        tool_res = {"cancelled": True}

                    # Interpret tool decision into raw field and boolean, matching prior logic
                    raw_field = None
                    is_tool = False
                    raw_txt = (tool_res or {}).get("text") if tool_res else None
                    if isinstance(raw_txt, str):
                        raw_stripped = raw_txt.strip()
                        if raw_stripped:
                            if raw_stripped.startswith("["):
                                try:
                                    parsed = json.loads(raw_stripped)
                                    if isinstance(parsed, list):
                                        raw_field = parsed
                                        is_tool = len(parsed) > 0
                                    else:
                                        raw_field = raw_stripped
                                except Exception:
                                    raw_field = raw_stripped
                                    is_tool = raw_stripped != "[]"
                            else:
                                raw_field = raw_stripped
                                is_tool = False

                    if is_tool:
                        # Abort chat and do NOT emit buffered text
                        session_active_req[session_id] = "CANCELLED"
                        try:
                            await get_chat_engine().abort_request(chat_req_id)
                        except Exception:
                            pass
                        try:
                            producer_task.cancel()
                        except Exception:
                            pass
                        # cleanup tool req id tracking
                        try:
                            session_tool_req.pop(session_id, None)
                        except Exception:
                            pass
                        await ws.send_text(json.dumps({"type": "toolcall", "status": "yes", "raw": raw_field}))
                        await ws.send_text(json.dumps({"type": "done", "usage": {}}))
                        return
                    else:
                        # Tool says NO (or timed out): flush buffer once, then continue streaming
                        flushing = True
                        await ws.send_text(json.dumps({"type": "toolcall", "status": "no", "raw": raw_field}))
                        if buffer:
                            joined = "".join(buffer)
                            await ws.send_text(json.dumps({"type": "token", "text": joined}))
                            final_text += joined
                            buffer.clear()
                        # cleanup tool req id tracking
                        try:
                            session_tool_req.pop(session_id, None)
                        except Exception:
                            pass

                    # Continue until producer finishes the stream
                    await producer_task

                    # finalize with optional punctuation fixing
                    if TEXTPROC_ENABLE:
                        punct_fixed = ensure_proper_ending_punctuation(final_text)
                        if len(punct_fixed) > len(final_text):
                            await ws.send_text(json.dumps({"type": "token", "text": punct_fixed[len(final_text):]}))
                        await ws.send_text(json.dumps({"type": "final", "normalized_text": punct_fixed}))
                    else:
                        await ws.send_text(json.dumps({"type": "final", "normalized_text": final_text}))

                    await ws.send_text(json.dumps({"type": "done", "usage": {}}))

                task = asyncio.create_task(_run_start())
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
                        # abort tool request via tracked tool req id when available
                        tr = session_tool_req.get(session_id)
                        if tr:
                            await get_tool_engine().abort_request(tr)
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
                    priority=1,
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
                    priority=1,
                )
                async for _ in stream:
                    break
                await ws.send_text(json.dumps({"type": "warmed", "segment": "history", "bytes": len(history_text)}))

            elif msg["type"] == "set_persona":
                # Runtime switch for assistant gender / style / raw persona
                if not session_id:
                    await ws.send_text(json.dumps({"type": "error", "message": "no active session"}))
                    continue
                changed: Dict[str, Any] = {}
                g = _norm_gender(msg.get("assistant_gender"))
                if g is not None:
                    session_meta[session_id]["assistant_gender"] = g
                    changed["assistant_gender"] = g
                if "persona_style" in msg and msg["persona_style"]:
                    style = msg["persona_style"].strip()
                    if style not in ALLOWED_PERSONALITIES:
                        await ws.send_text(json.dumps({
                            "type": "error",
                            "message": f"invalid persona_style '{style}'; allowed: {sorted(ALLOWED_PERSONALITIES)}"
                        }))
                        continue
                    session_meta[session_id]["persona_style"] = style
                    changed["persona_style"] = style
                if "persona_text" in msg:
                    # explicit None/empty clears the override
                    ov = msg.get("persona_text") or None
                    session_meta[session_id]["persona_text_override"] = ov
                    changed["persona_text_override"] = bool(ov)

                # -------- ACK: persona/gender switch applied --------
                await ws.send_text(json.dumps({
                    "type": "ack",
                    "for": "set_persona",
                    "ok": True,
                    "session_id": session_id,
                    "changed": changed,
                    "assistant_gender": session_meta[session_id]["assistant_gender"],
                    "persona_style": session_meta[session_id]["persona_style"],
                    "persona_text_override": bool(session_meta[session_id]["persona_text_override"]),
                }))

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
                tr = session_tool_req.get(session_id)
                if tr:
                    await get_tool_engine().abort_request(tr)
            except Exception:
                pass
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))


