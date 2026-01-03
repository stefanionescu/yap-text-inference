from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.helpers.metrics import SessionContext
from tests.helpers.websocket import build_start_payload as build_ws_start_payload

from .personas import PersonaDefinition


@dataclass
class LiveSession:
    """Live test session state.
    
    Note: chat_prompt is always required - the server requires a system prompt
    when DEPLOY_CHAT is enabled.
    """
    
    session_id: str
    persona: PersonaDefinition
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def build_start_payload(self, user_text: str) -> dict[str, Any]:
        """Build the start message payload for a conversation turn."""
        ctx = SessionContext(
            session_id=self.session_id,
            gender=self.persona.gender,
            personality=self.persona.personality,
            chat_prompt=self.persona.prompt,
            sampling=self.sampling,
        )
        return build_ws_start_payload(ctx, user_text, history=self.history)

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})

__all__ = ["LiveSession"]


