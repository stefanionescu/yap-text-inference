"""Concurrent execution: tool and chat models run in parallel."""

import asyncio
import contextlib
import logging
import json
import os
import uuid
from fastapi import WebSocket

from .tool_runner import run_toolcall
from .tool_parser import parse_tool_result
from .chat_streamer import run_chat_stream
from ..engines import get_chat_engine, get_tool_engine
from ..handlers.session_manager import session_manager

logger = logging.getLogger(__name__)


async def run_concurrent_execution(
    ws: WebSocket,
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
) -> None:
    """Execute concurrent tool and chat workflow with buffering.
    
    Args:
        ws: WebSocket connection
        session_id: Session identifier
        static_prefix: Static persona prefix
        runtime_text: Runtime persona text
        history_text: Conversation history
        user_utt: User utterance
    """
    tool_hard_timeout_ms = float(os.getenv("TOOL_HARD_TIMEOUT_MS", "300"))
    prebuffer_max_chars = int(os.getenv("PREBUFFER_MAX_CHARS", "1000"))
    logger.info(
        f"concurrent_exec: session_id={session_id} tool_timeout_ms={tool_hard_timeout_ms} prebuffer={prebuffer_max_chars}"
    )
    
    # Start both tool and chat coroutines concurrently
    tool_req_id = f"tool-{uuid.uuid4()}"
    chat_req_id = f"chat-{uuid.uuid4()}"
    
    session_manager.set_tool_request(session_id, tool_req_id)
    session_manager.set_active_request(session_id, chat_req_id)  # chat gets active req id for cancellation
    
    # Start tool model with shared history for KV cache efficiency
    tool_coro = run_toolcall(session_id, user_utt, history_text, request_id=tool_req_id, mark_active=False)
    logger.info(f"concurrent_exec: tool start req_id={tool_req_id}")
    
    # Start chat model  
    chat_stream = run_chat_stream(
        session_id,
        static_prefix,
        runtime_text,
        history_text,
        user_utt,
        request_id=chat_req_id,
    )
    logger.info(f"concurrent_exec: chat start req_id={chat_req_id}")
    
    # Buffer to accumulate chat tokens while waiting for tool decision
    chat_buffer = ""
    tool_decision_ready = False
    tool_result = None

    # Create task for tool result collection
    async def collect_tool_result():
        """Collect tool result with timeout handling."""
        nonlocal tool_result, tool_decision_ready
        try:
            if tool_hard_timeout_ms < 0:
                tool_result = await tool_coro
            else:
                tool_result = await asyncio.wait_for(tool_coro, timeout=tool_hard_timeout_ms / 1000.0)
        except asyncio.TimeoutError:
            try:
                if session_manager.session_tool_req.get(session_id):
                    await (await get_tool_engine()).abort_request(
                        session_manager.session_tool_req.get(session_id, "")
                    )
            except Exception:
                pass
            tool_result = {"cancelled": True}
        finally:
            tool_decision_ready = True

    # Start tool collection task
    tool_task = asyncio.create_task(collect_tool_result())

    try:
        # Consume chat stream while also reacting immediately if tool decision arrives first
        aiter = chat_stream.__aiter__()
       
        while True:
            # Create a task to await the next chat chunk
            next_chunk_task = asyncio.create_task(aiter.__anext__())

            done, pending = await asyncio.wait({tool_task, next_chunk_task}, return_when=asyncio.FIRST_COMPLETED)

            if next_chunk_task in done:
                try:
                    chunk = next_chunk_task.result()
                except StopAsyncIteration:
                    # Chat stream finished before producing any new chunk
                    # Ensure tool task completed so we can proceed
                    if not tool_task.done():
                        await tool_task
                    logger.info("concurrent_exec: chat stream ended before tool decision")
                    break

                if tool_decision_ready:
                    # Tool decision arrived: capture this first chunk then break to process decision
                    chat_buffer += chunk
                    logger.info(f"concurrent_exec: tool decision ready; first chat chunk len={len(chunk)}")
                    break

                chat_buffer += chunk
                if len(chat_buffer) >= prebuffer_max_chars:
                    await ws.send_text(json.dumps({"type": "token", "text": chat_buffer}))
                    logger.info(f"concurrent_exec: flushed prebuffer len={len(chat_buffer)}")
                    chat_buffer = ""

                # Continue loop to fetch next chunk (tool decision not ready yet)
                continue

            # Tool task completed first
            if tool_task in done:
                tool_decision_ready = True
                # Cancel waiting for the next chunk to avoid blocking; do NOT await it
                try:
                    next_chunk_task.cancel()
                except Exception:
                    pass
                logger.info("concurrent_exec: tool decision arrived before first chat chunk (cancelled chat next_chunk)")
                break

        # Ensure tool task completes
        if not tool_decision_ready:
            await tool_task
        
        # Parse tool decision
        raw_field, is_tool = parse_tool_result(tool_result)
        _txt = (tool_result or {}).get("text") if tool_result else None
        logger.info(f"concurrent_exec: tool_result is_tool={is_tool} text_len={(len(_txt) if isinstance(_txt, str) else 0)}")
        
        # Cleanup tool req id tracking (no longer in-flight)
        try:
            session_manager.session_tool_req.pop(session_id, None)
        except Exception:
            pass
        
        if is_tool:
            # Tool detected: cancel first chat stream, ignore buffered tokens, start new chat stream
            try:
                await (await get_chat_engine()).abort_request(chat_req_id)
            except Exception:
                pass
            
            # Send toolcall response
            await ws.send_text(json.dumps({
                "type": "toolcall", 
                "status": "yes", 
                "raw": raw_field
            }))
            logger.info("concurrent_exec: sent toolcall yes")
            
            # Start new chat stream (ignoring buffered tokens from first stream)
            new_chat_req_id = f"chat-{uuid.uuid4()}"
            session_manager.set_active_request(session_id, new_chat_req_id)
            
            new_chat_stream = run_chat_stream(
                session_id,
                static_prefix,
                runtime_text,
                history_text,
                user_utt,
                request_id=new_chat_req_id,
            )
            logger.info(f"concurrent_exec: new chat stream after tool yes req_id={new_chat_req_id}")
            
            # Stream from the new chat stream
            final_text = ""
            async for chunk in new_chat_stream:
                await ws.send_text(json.dumps({"type": "token", "text": chunk}))
                final_text += chunk
            
            # Send final text
            await ws.send_text(json.dumps({
                "type": "final", 
                "normalized_text": final_text
            }))
            await ws.send_text(json.dumps({"type": "done", "usage": {}}))
            logger.info(f"concurrent_exec: done after tool yes chars={len(final_text)}")
            return
        
        # Tool says NO: flush buffered chat text and continue streaming
        await ws.send_text(json.dumps({
            "type": "toolcall", 
            "status": "no", 
            "raw": raw_field
        }))
        logger.info("concurrent_exec: sent toolcall no")
        
        # Flush any buffered chat text
        if chat_buffer:
            await ws.send_text(json.dumps({"type": "token", "text": chat_buffer}))
            logger.info(f"concurrent_exec: flushed buffered chat len={len(chat_buffer)}")
        
        # Continue streaming the rest of chat output
        final_text = chat_buffer
        # Continue consuming from the same iterator we used above
        async for chunk in aiter:
            await ws.send_text(json.dumps({"type": "token", "text": chunk}))
            final_text += chunk
        
        # Send final text
        await ws.send_text(json.dumps({
            "type": "final", 
            "normalized_text": final_text
        }))
        await ws.send_text(json.dumps({"type": "done", "usage": {}}))
        logger.info(f"concurrent_exec: done after tool no chars={len(final_text)}")
    
    except Exception as e:
        # Clean up on any error
        try:
            await (await get_chat_engine()).abort_request(chat_req_id)
        except Exception:
            pass
        try:
            if session_manager.session_tool_req.get(session_id):
                await (await get_tool_engine()).abort_request(
                    session_manager.session_tool_req.get(session_id, "")
                )
        except Exception:
            pass
        logger.exception("concurrent_exec: error")
        raise
