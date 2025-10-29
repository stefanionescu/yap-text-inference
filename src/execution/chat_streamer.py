"""Chat streaming logic for real-time text generation."""

import asyncio
import os
import time
import uuid
from typing import AsyncGenerator, Optional
import logging

from vllm.sampling_params import SamplingParams

from ..engines import get_chat_engine
from ..persona import build_chat_prompt_with_prefix
from ..config import CHAT_MAX_OUT, STREAM_FLUSH_MS
from ..handlers.session_manager import session_manager

logger = logging.getLogger(__name__)

# --- Chat sampling defaults ---
CHAT_TEMPERATURE = 0.55
CHAT_TOP_P = 0.90
CHAT_TOP_K = 60
CHAT_MIN_P = 0.05
CHAT_REPEAT_PENALTY = 1.10

# --- Extra STOP sequences for chat model ---
STOP = [" |", "  |", "<|im_end|>", "|im_end|>", " ‍♀️", " ‍♂️"]


async def run_chat_stream(
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    request_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream chat generation with optional micro-coalescing.
    
    Args:
        session_id: Session identifier
        static_prefix: Static persona prefix
        runtime_text: Runtime persona text
        history_text: Conversation history
        user_utt: User utterance
        request_id: Optional request ID
        
    Yields:
        Text chunks from chat generation
    """
    req_id = request_id or f"chat-{uuid.uuid4()}"
    session_manager.set_active_request(session_id, req_id)

    # Avoid per-request generator when using FlashInfer backend to prevent fallback
    backend = (os.getenv("VLLM_ATTENTION_BACKEND", "").upper() or "").strip()
    params_kwargs = dict(
        temperature=CHAT_TEMPERATURE,
        top_p=CHAT_TOP_P,
        top_k=CHAT_TOP_K,
        min_p=CHAT_MIN_P,
        repetition_penalty=CHAT_REPEAT_PENALTY,
        max_tokens=CHAT_MAX_OUT,
        stop=STOP + ["<|end|>", "</s>"],
    )
    if backend != "FLASHINFER":
        params_kwargs["seed"] = session_manager.get_session_seed(session_id)
    params = SamplingParams(**params_kwargs)

    prompt = build_chat_prompt_with_prefix(static_prefix, runtime_text, history_text, user_utt)
    # Realtime mode: emit ASAP. Optional micro-coalescer if STREAM_FLUSH_MS>0
    last_text = ""
    ttfb_logged = False
    t_start = time.perf_counter()
    
    # Robust env parsing; treat blank/None as 0
    env_flush = os.getenv("STREAM_FLUSH_MS", "")
    try:
        flush_ms = float(env_flush) if env_flush.strip() else float(STREAM_FLUSH_MS)
    except Exception:
        flush_ms = float(STREAM_FLUSH_MS)
    
    gen_timeout_s = float(os.getenv("GEN_TIMEOUT_S", "60"))
    logger.info(
        f"chat_stream: start session_id={session_id} req_id={req_id} max_out={params.max_tokens} "
        f"flush_ms={flush_ms} gen_timeout_s={gen_timeout_s}"
    )
    
    buf = []
    last_flush = time.perf_counter()

    async def _iter_stream():
        """Internal generator for chat output."""
        stream = (await get_chat_engine()).generate(
            prompt=prompt,
            sampling_params=params,
            request_id=req_id,
            priority=0,
        )
        async for out in stream:
            yield out

    try:
        # Python 3.8+ compatible timeout handling without asyncio.timeout
        deadline = time.perf_counter() + gen_timeout_s
        aiter = _iter_stream().__aiter__()
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                out = await asyncio.wait_for(aiter.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                break

            # Check if request was cancelled
            if session_manager.session_active_req.get(session_id) != req_id:
                await (await get_chat_engine()).abort_request(req_id)
                return

            if not out.outputs:
                continue

            full_text = out.outputs[0].text
            delta = full_text[len(last_text):]
            if not delta:
                continue

            last_text = full_text

            if flush_ms <= 0:
                # Pure realtime: send immediately
                yield delta
            else:
                # Buffer mode: accumulate and flush periodically
                buf.append(delta)
                now = time.perf_counter()
                if (now - last_flush) * 1000.0 >= flush_ms:
                    yield "".join(buf)
                    buf.clear()
                    last_flush = now
                    logger.info(f"chat_stream: flushed coalesced chunk session_id={session_id} req_id={req_id}")

            # Log TTFB once after first delta
            if not ttfb_logged:
                ttfb_ms = (time.perf_counter() - t_start) * 1000.0
                logger.info(f"chat_stream: first token session_id={session_id} req_id={req_id} ttfb_ms={ttfb_ms:.1f}")
                ttfb_logged = True

    except asyncio.TimeoutError:
        try:
            await (await get_chat_engine()).abort_request(req_id)
        except Exception:
            pass
        logger.info(f"chat_stream: timeout session_id={session_id} req_id={req_id}")
        return

    # Flush any tail if coalescer was on
    if flush_ms > 0 and buf:
        yield "".join(buf)
        logger.info(f"chat_stream: flushed tail session_id={session_id} req_id={req_id} len={len(''.join(buf))}")
    logger.info(f"chat_stream: end session_id={session_id} req_id={req_id} total_len={len(last_text)} ms={(time.perf_counter()-t_start)*1000.0:.1f}")
