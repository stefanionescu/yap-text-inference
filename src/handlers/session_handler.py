"""Session handler for WebSocket connections."""

import asyncio
from typing import Dict, Any, Optional

from ..config import CHAT_MODEL, TOOL_MODEL, HISTORY_MAX_TOKENS, DEPLOY_CHAT, DEPLOY_TOOL
from ..tokens import count_tokens_chat, trim_history_preserve_messages_chat
from ..utils.time_utils import format_session_timestamp


class SessionHandler:
    """Handles session metadata and lifecycle."""

    def __init__(self):
        # Per-session metadata: timestamp string and persona/model config
        self.session_meta: Dict[str, Dict[str, Any]] = {}

        # Rolling history per session (server-managed)
        self.session_history: Dict[str, str] = {}

        # Track active session tasks/requests
        self.session_tasks: Dict[str, asyncio.Task] = {}
        self.session_active_req: Dict[str, str] = {}

        # Track in-flight tool req ids (when tool router runs in parallel with chat)
        self.session_tool_req: Dict[str, str] = {}

    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Initialize session metadata if it doesn't exist.

        Args:
            session_id: Unique session identifier

        Returns:
            Session metadata dict
        """
        if session_id not in self.session_meta:
            now_str = format_session_timestamp()

            self.session_meta[session_id] = {
                "now_str": now_str,
                # defaults that can be overridden on start
                "chat_gender": None,
                "chat_personality": None,
                "chat_prompt": None,
                "tool_prompt": None,
                # expose models (handy for client logs) - only include if deployed
                "chat_model": CHAT_MODEL if DEPLOY_CHAT else None,
                "tool_model": TOOL_MODEL if DEPLOY_TOOL else None,
            }

        self.session_history.setdefault(session_id, "")

        return self.session_meta[session_id]

    def update_session_config(
        self,
        session_id: str,
        chat_gender: Optional[str] = None,
        chat_personality: Optional[str] = None,
        chat_prompt: Optional[str] = None,
        tool_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update session configuration.

        Args:
            session_id: Session identifier
            chat_gender: 'female' or 'male'
            chat_personality: validated personality string
            chat_prompt: Raw chat prompt provided by client
            tool_prompt: Raw tool prompt provided by client

        Returns:
            Dict of changed fields
        """
        if session_id not in self.session_meta:
            self.initialize_session(session_id)

        changed = {}

        if chat_gender is not None:
            self.session_meta[session_id]["chat_gender"] = chat_gender
            changed["chat_gender"] = chat_gender

        if chat_personality is not None:
            cpers = chat_personality or None
            if isinstance(cpers, str):
                cpers = cpers.lower()
            self.session_meta[session_id]["chat_personality"] = cpers
            changed["chat_personality"] = cpers

        if chat_prompt is not None:
            # explicit None/empty clears the prompt
            cp = chat_prompt or None
            self.session_meta[session_id]["chat_prompt"] = cp
            changed["chat_prompt"] = bool(cp)

        if tool_prompt is not None:
            tp = tool_prompt or None
            self.session_meta[session_id]["tool_prompt"] = tp
            changed["tool_prompt"] = bool(tp)

        return changed

    def get_session_config(self, session_id: str) -> Dict[str, Any]:
        """Get current session configuration.

        Args:
            session_id: Session identifier

        Returns:
            Session configuration dict
        """
        if session_id not in self.session_meta:
            return {}
        return self.session_meta[session_id].copy()

    def set_active_request(self, session_id: str, request_id: str) -> None:
        """Set the active request ID for a session.

        Args:
            session_id: Session identifier
            request_id: Request identifier
        """
        self.session_active_req[session_id] = request_id

    def set_tool_request(self, session_id: str, request_id: str) -> None:
        """Set the tool request ID for a session.

        Args:
            session_id: Session identifier
            request_id: Tool request identifier
        """
        self.session_tool_req[session_id] = request_id

    def cancel_session_requests(self, session_id: str) -> None:
        """Cancel all requests for a session.

        Args:
            session_id: Session identifier
        """
        self.session_active_req[session_id] = "CANCELLED"

        # Cancel session task
        task = self.session_tasks.get(session_id)
        if task:
            task.cancel()

    def cleanup_session_requests(self, session_id: str) -> Dict[str, str]:
        """Clean up session request tracking and return request IDs.

        Args:
            session_id: Session identifier

        Returns:
            Dict with 'active' and 'tool' request IDs
        """
        active_req = self.session_active_req.get(session_id, "")
        tool_req = self.session_tool_req.pop(session_id, "")

        return {"active": active_req, "tool": tool_req}

    def get_history_text(self, session_id: str) -> str:
        """Return the server-tracked history for the session."""
        return self.session_history.get(session_id, "")

    def set_history_text(self, session_id: str, history_text: str) -> str:
        """Set (and trim) the server-tracked history for the session."""
        normalized = self._normalize_history(history_text)
        self.session_history[session_id] = normalized
        return normalized

    def append_history_turn(self, session_id: str, user_utt: str, assistant_text: str) -> str:
        """Append a formatted user/assistant turn to the stored history."""
        turn = self._format_turn(user_utt, assistant_text)
        if not turn:
            return self.session_history.get(session_id, "")

        existing = self.session_history.get(session_id, "")
        combined = f"{existing}\n\n{turn}".strip() if existing.strip() else turn
        normalized = self._normalize_history(combined)
        self.session_history[session_id] = normalized
        return normalized

    def clear_session_state(self, session_id: str) -> None:
        """Clear all stored state for a session."""
        self.session_meta.pop(session_id, None)
        self.session_tasks.pop(session_id, None)
        self.session_active_req.pop(session_id, None)
        self.session_tool_req.pop(session_id, None)
        self.session_history.pop(session_id, None)

    def _normalize_history(self, history_text: str) -> str:
        text = (history_text or "").strip()
        if not text:
            return ""
        # Only trim history if chat model is deployed (history trimming uses chat tokenizer)
        if DEPLOY_CHAT and count_tokens_chat(text) > HISTORY_MAX_TOKENS:
            text = trim_history_preserve_messages_chat(text, HISTORY_MAX_TOKENS)
        return text

    @staticmethod
    def _format_turn(user_utt: str, assistant_text: str) -> str:
        user = (user_utt or "").strip()
        assistant = (assistant_text or "").strip()
        if not user and not assistant:
            return ""
        return f"User: {user}\nAssistant: {assistant}".strip()


# Global session handler instance
session_handler = SessionHandler()


