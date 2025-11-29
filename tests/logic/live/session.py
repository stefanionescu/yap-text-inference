from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tests.prompts.toolcall import TOOLCALL_PROMPT

from .personas import PersonaDefinition


@dataclass
class LiveSession:
    session_id: str
    persona: PersonaDefinition
    include_chat_prompt: bool = True
    tool_prompt: str | None = TOOLCALL_PROMPT
    history: str = ""
    sampling: dict[str, float | int] | None = None

    def build_start_payload(self, user_text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "start",
            "session_id": self.session_id,
            "gender": self.persona.gender,
            "personality": self.persona.personality,
            "history_text": self.history,
            "user_utterance": user_text,
        }
        if self.include_chat_prompt:
            payload["chat_prompt"] = self.persona.prompt
        if self.tool_prompt is not None:
            payload["tool_prompt"] = self.tool_prompt
        if "chat_prompt" not in payload and "tool_prompt" not in payload:
            raise ValueError("prompt_mode must enable chat and/or tool prompts for live sessions")
        if self.sampling:
            payload["sampling"] = self.sampling
        return payload

    def build_persona_payload(self, persona: PersonaDefinition) -> dict[str, Any]:
        if not self.include_chat_prompt:
            raise ValueError("chat prompts are disabled for this session; persona updates are unavailable")
        return {
            "type": "chat_prompt",
            "session_id": self.session_id,
            "gender": persona.gender,
            "personality": persona.personality,
            "chat_prompt": persona.prompt,
            "history_text": self.history,
        }

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()

    def replace_persona(self, persona: PersonaDefinition) -> None:
        self.persona = persona


__all__ = ["LiveSession"]


