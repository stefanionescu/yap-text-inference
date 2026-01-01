from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.config import DEFAULT_PERSONALITIES

from .personas import PersonaDefinition


@dataclass
class LiveSession:
    session_id: str
    persona: PersonaDefinition
    include_chat_prompt: bool = True
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def build_start_payload(self, user_text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "start",
            "session_id": self.session_id,
            "gender": self.persona.gender,
            "personality": self.persona.personality,
            "personalities": DEFAULT_PERSONALITIES,
            "history": self.history,
            "user_utterance": user_text,
        }
        if self.include_chat_prompt:
            payload["chat_prompt"] = self.persona.prompt
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
        }

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})

    def replace_persona(self, persona: PersonaDefinition) -> None:
        self.persona = persona


__all__ = ["LiveSession"]


