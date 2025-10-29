"""WebSocket message handlers for different message types."""

import asyncio
import json
import uuid
import logging
from typing import Dict, Any
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..config import (
    HISTORY_MAX_TOKENS, USER_UTT_MAX_TOKENS,
    CONCURRENT_MODEL_CALL,
    DEPLOY_CHAT, DEPLOY_TOOL,
)
from ..engines import get_chat_engine
from ..persona import get_static_prefix, compose_persona_runtime
from ..tokens import (
    count_tokens, trim_text_to_token_limit,
    trim_history_preserve_messages
)
from ..utils.validation import (
    normalize_gender, validate_persona_style, validate_user_identity,
    ALLOWED_PERSONALITIES
)
from ..handlers.session_manager import session_manager
from ..execution.sequential_executor import run_sequential_execution
from ..execution.concurrent_executor import run_concurrent_execution
from ..execution.chat_streamer import run_chat_stream
from ..execution.tool_runner import run_toolcall
from ..execution.tool_parser import parse_tool_result

logger = logging.getLogger(__name__)


async def handle_start_message(ws: WebSocket, msg: Dict[str, Any], session_id: str) -> None:
    """Handle 'start' message type.
    
    Args:
        ws: WebSocket connection
        msg: Message data
        session_id: Session identifier
    """
    # Initialize session metadata
    logger.info(
        f"handle_start: session_id={session_id} gender_in={msg.get('assistant_gender')} "
        f"style_in={msg.get('persona_style')} hist_len={len(msg.get('history_text',''))} "
        f"user_len={len(msg.get('user_utterance',''))}"
    )
    session_config = session_manager.initialize_session(session_id)
    
    # Pull fixed values for this session
    sess_seed = session_config["seed"]
    sess_now_str = session_config["now_str"]

    # Require assistant_gender & persona_style on start; allow override persona
    incoming_gender = normalize_gender(msg.get("assistant_gender"))
    if incoming_gender is None and session_config.get("assistant_gender") is None:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "assistant_gender is required on start: use 'female'/'male' (or 'woman'/'man')."
        }))
        logger.info("handle_start: error → missing assistant_gender")
        return
    
    if incoming_gender is not None:
        session_manager.update_session_config(session_id, assistant_gender=incoming_gender)

    # Validate persona_style: required at start and must be allowed
    incoming_style = (msg.get("persona_style") or "").strip()
    if not session_config.get("persona_text_override"):
        if not incoming_style and session_config.get("persona_style") is None:
            await ws.send_text(json.dumps({
                "type": "error",
                "message": f"persona_style is required on start; allowed: {sorted(ALLOWED_PERSONALITIES)}"
            }))
            logger.info("handle_start: error → missing persona_style")
            return
        if incoming_style:
            if not validate_persona_style(incoming_style):
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": f"invalid persona_style '{incoming_style}'; allowed: {sorted(ALLOWED_PERSONALITIES)}"
                }))
                logger.info("handle_start: error → invalid persona_style")
                return
            session_manager.update_session_config(session_id, persona_style=incoming_style)

    # Optional raw persona override for this session
    persona_override = msg.get("persona_text") or None
    if persona_override:
        session_manager.update_session_config(session_id, persona_text_override=persona_override)

    # Get updated config after changes
    updated_config = session_manager.get_session_config(session_id)

    # Persona resolution for prefix-sharing: static prefix + small runtime
    if updated_config["persona_text_override"]:
        static_prefix = updated_config["persona_text_override"]
        runtime_text = ""
    else:
        static_prefix = get_static_prefix(
            style=updated_config["persona_style"],
            gender=updated_config["assistant_gender"] or "woman",
        )
        runtime_text = compose_persona_runtime(
            user_identity=validate_user_identity(msg.get("user_identity", "non-binary")),
            now_str=sess_now_str,
        )

    # Send ACK: session start / (re)config pinned
    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "start",
        "ok": True,
        "session_id": session_id,
        "seed": sess_seed,
        "now": sess_now_str,
        "assistant_gender": updated_config["assistant_gender"],
        "persona_style": updated_config["persona_style"],
        "persona_text_override": bool(updated_config["persona_text_override"]),
        "models": {
            "chat": updated_config["chat_model"],
            "tool": updated_config["tool_model"]
        }
    }))
    logger.info(
        f"handle_start: ack sent session_id={session_id} chat_model={updated_config['chat_model']} "
        f"tool_model={updated_config['tool_model']}"
    )

    # Process history and user utterance
    history_text = msg.get("history_text", "")
    user_utt = msg["user_utterance"]
    
    # Trim user utterance to first USER_UTT_MAX_TOKENS (exact)
    user_utt = trim_text_to_token_limit(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    
    # Trim rolling history to HISTORY_MAX_TOKENS, keep most recent
    # Use message-boundary-aware trimming to avoid partial messages
    if count_tokens(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages(
            history_text,
            HISTORY_MAX_TOKENS,
        )

    # Choose execution based on deploy mode and concurrency flag
    async def _run_start():
        if DEPLOY_CHAT and DEPLOY_TOOL:
            if CONCURRENT_MODEL_CALL:
                logger.info(f"handle_start: concurrent execution session_id={session_id}")
                await run_concurrent_execution(ws, session_id, static_prefix, runtime_text, history_text, user_utt)
            else:
                logger.info(f"handle_start: sequential execution session_id={session_id}")
                await run_sequential_execution(ws, session_id, static_prefix, runtime_text, history_text, user_utt)
            return

        if DEPLOY_CHAT and not DEPLOY_TOOL:
            # Chat-only deployment: stream chat tokens and finalize
            logger.info(f"handle_start: chat-only streaming session_id={session_id}")
            final_text = ""
            async for chunk in run_chat_stream(
                session_id,
                static_prefix,
                runtime_text,
                history_text,
                user_utt,
            ):
                await ws.send_text(json.dumps({"type": "token", "text": chunk}))
                final_text += chunk

            await ws.send_text(json.dumps({
                "type": "final",
                "normalized_text": final_text
            }))
            await ws.send_text(json.dumps({"type": "done", "usage": {}}))
            logger.info(f"handle_start: chat-only done session_id={session_id} chars={len(final_text)}")
            return

        if DEPLOY_TOOL and not DEPLOY_CHAT:
            # Tool-only deployment: run tool router, emit decision, and finalize
            logger.info(f"handle_start: tool-only routing session_id={session_id}")
            tool_res = await run_toolcall(session_id, user_utt, history_text, mark_active=False)
            raw_field, is_tool = parse_tool_result(tool_res)
            await ws.send_text(json.dumps({
                "type": "toolcall",
                "status": "yes" if is_tool else "no",
                "raw": raw_field,
            }))
            await ws.send_text(json.dumps({
                "type": "final",
                "normalized_text": ""
            }))
            await ws.send_text(json.dumps({"type": "done", "usage": {}}))
            logger.info(f"handle_start: tool-only done session_id={session_id} is_tool={is_tool}")
            return

    task = asyncio.create_task(_run_start())
    session_manager.session_tasks[session_id] = task


async def handle_cancel_message(ws: WebSocket, session_id: str) -> None:
    """Handle 'cancel' message type.
    
    Args:
        ws: WebSocket connection
        session_id: Session identifier
    """
    if session_id:
        session_manager.cancel_session_requests(session_id)
        req_info = session_manager.cleanup_session_requests(session_id)
        
        # Abort active chat request
        try:
            if req_info["active"]:
                await (await get_chat_engine()).abort_request(req_info["active"])
        except Exception:
            pass
        
        # Abort tool request if exists
        try:
            if req_info["tool"]:
                from ..engines import get_tool_engine
                await (await get_tool_engine()).abort_request(req_info["tool"])
        except Exception:
            pass
    
    await ws.send_text(json.dumps({"type": "done", "cancelled": True}))


async def handle_warm_persona_message(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Handle 'warm_persona' message type.
    
    Args:
        ws: WebSocket connection
        msg: Message data
    """
    # Warm the STATIC PREFIX only for a given style/gender (prefix sharing)
    persona_override = msg.get("persona_text")
    if persona_override:
        static_prefix = persona_override
    else:
        gender = normalize_gender(msg.get("assistant_gender")) or "woman"
        static_prefix = get_static_prefix(
            style=msg.get("persona_style", "wholesome"),
            gender=gender,
        )
    
    warm_prompt = f"<|persona|>\n{static_prefix.strip()}\n<|assistant|>\n"
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    req_id = f"warm-p-{uuid.uuid4()}"
    
    stream = (await get_chat_engine()).generate(
        prompt=warm_prompt,
        sampling_params=params,
        request_id=req_id,
        priority=1,
    )
    async for _ in stream:
        break
    
    await ws.send_text(json.dumps({
        "type": "warmed", 
        "segment": "persona_static", 
        "bytes": len(static_prefix)
    }))


async def handle_warm_history_message(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Handle 'warm_history' message type.
    
    Args:
        ws: WebSocket connection
        msg: Message data
    """
    history_text = msg.get("history_text", "")
    if count_tokens(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages(
            history_text,
            HISTORY_MAX_TOKENS,
        )
    
    warm_prompt = f"<|history|>\n{history_text.strip()}\n<|assistant|>\n"
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    req_id = f"warm-h-{uuid.uuid4()}"
    
    stream = (await get_chat_engine()).generate(
        prompt=warm_prompt,
        sampling_params=params,
        request_id=req_id,
        priority=1,
    )
    async for _ in stream:
        break
    
    await ws.send_text(json.dumps({
        "type": "warmed", 
        "segment": "history", 
        "bytes": len(history_text)
    }))


async def handle_set_persona_message(ws: WebSocket, msg: Dict[str, Any], session_id: str) -> None:
    """Handle 'set_persona' message type.
    
    Args:
        ws: WebSocket connection
        msg: Message data
        session_id: Session identifier
    """
    if not session_id:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session"}))
        return

    # Runtime switch for assistant gender / style / raw persona
    changed = {}
    
    g = normalize_gender(msg.get("assistant_gender"))
    if g is not None:
        changed.update(session_manager.update_session_config(session_id, assistant_gender=g))
    
    if "persona_style" in msg and msg["persona_style"]:
        style = msg["persona_style"].strip()
        if not validate_persona_style(style):
            await ws.send_text(json.dumps({
                "type": "error",
                "message": f"invalid persona_style '{style}'; allowed: {sorted(ALLOWED_PERSONALITIES)}"
            }))
            return
        changed.update(session_manager.update_session_config(session_id, persona_style=style))
    
    if "persona_text" in msg:
        # explicit None/empty clears the override
        ov = msg.get("persona_text") or None
        changed.update(session_manager.update_session_config(session_id, persona_text_override=ov))

    # Get updated config for response
    config = session_manager.get_session_config(session_id)

    # Send ACK: persona/gender switch applied
    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "set_persona",
        "ok": True,
        "session_id": session_id,
        "changed": changed,
        "assistant_gender": config["assistant_gender"],
        "persona_style": config["persona_style"],
        "persona_text_override": bool(config["persona_text_override"]),
    }))
