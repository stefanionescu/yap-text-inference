"""Tool execution logic for processing tool calls."""

import asyncio
import os
import uuid
from typing import Optional, Dict, Any

from vllm.sampling_params import SamplingParams

from ..engines import get_tool_engine
from ..persona import build_hammer_prompt, build_hammer_prompt_with_history
from ..config import TOOL_MAX_OUT, TOOL_HISTORY_TOKENS, EXACT_TOKEN_TRIM
from ..tokens import trim_history_for_tool_sharing
from ..handlers.session_manager import session_manager

# --- Toolcall sampling defaults ---
TOOL_TEMPERATURE = 0.05
TOOL_TOP_P = 1.0
TOOL_TOP_K = 1
TOOL_STOP = ["\n", "</s>"]


async def run_toolcall(
    session_id: str,
    user_utt: str,
    history_text: str = "",
    request_id: Optional[str] = None,
    mark_active: bool = True,
) -> Dict[str, Any]:
    """Execute a tool call with timeout handling and KV cache sharing.
    
    Args:
        session_id: Session identifier
        user_utt: User utterance to process
        history_text: Recent conversation history for context and KV sharing
        request_id: Optional request ID (generates one if not provided)
        mark_active: Whether to mark this as the active request
        
    Returns:
        Dict containing 'cancelled' bool and optionally 'text' with tool output
    """
    req_id = request_id or f"tool-{uuid.uuid4()}"
    
    if mark_active:
        session_manager.set_active_request(session_id, req_id)

    params = SamplingParams(
        temperature=TOOL_TEMPERATURE,
        top_p=TOOL_TOP_P,
        top_k=TOOL_TOP_K,
        max_tokens=TOOL_MAX_OUT,
        stop=TOOL_STOP,
        seed=session_manager.get_session_seed(session_id),
    )

    pieces = []
    tool_timeout_s = float(os.getenv("TOOL_TIMEOUT_S", "10"))

    # Trim history for tool model to enable KV cache sharing
    tool_history = trim_history_for_tool_sharing(
        history_text, 
        TOOL_HISTORY_TOKENS, 
        exact=EXACT_TOKEN_TRIM
    )

    async def _iter_tool():
        """Internal generator for tool output."""
        # Use enhanced prompt with history for better context and KV cache sharing
        if tool_history.strip():
            prompt = build_hammer_prompt_with_history(user_utt, tool_history)
        else:
            prompt = build_hammer_prompt(user_utt)
            
        stream = (await get_tool_engine()).generate(
            prompt=prompt,
            sampling_params=params,
            request_id=req_id,
            priority=1,
        )
        async for out in stream:
            yield out

    try:
        async with asyncio.timeout(tool_timeout_s):
            async for out in _iter_tool():
                # Check if this request was cancelled
                if (mark_active and 
                    session_manager.session_active_req.get(session_id) != req_id):
                    await (await get_tool_engine()).abort_request(req_id)
                    return {"cancelled": True}
                    
                if out.outputs:
                    pieces.append(out.outputs[0].text)
                    
    except asyncio.TimeoutError:
        try:
            await (await get_tool_engine()).abort_request(req_id)
        except Exception:
            pass
        return {"cancelled": True}

    text = "".join(pieces).strip()
    return {"cancelled": False, "text": text}
