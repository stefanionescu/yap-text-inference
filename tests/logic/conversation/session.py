from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

_test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

@dataclass
class ConversationSession:
    session_id: str
    gender: str
    personality: str
    chat_prompt: str | None
    tool_prompt: str | None
    history: str = ""
    sampling: dict[str, float | int] | None = None

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()


def build_start_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session.session_id,
        "gender": session.gender,
        "personality": session.personality,
        "history_text": session.history,
        "user_utterance": user_text,
    }
    if session.chat_prompt is not None:
        payload["chat_prompt"] = session.chat_prompt
    if session.tool_prompt is not None:
        payload["tool_prompt"] = session.tool_prompt
    if "chat_prompt" not in payload and "tool_prompt" not in payload:
        raise ValueError("Session configuration requires chat_prompt and/or tool_prompt")
    if session.sampling:
        payload["sampling"] = session.sampling
    return payload


__all__ = ["ConversationSession", "build_start_payload"]
