"""History orchestration for SessionState with explicit chat/tool storage."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Literal
from .settings import HistoryRuntimeConfig
from src.tokens.history import build_tool_history
from src.state.session import ChatMessage, HistoryTurn, SessionState
from .ops import get_user_texts, render_history, trim_chat_history, trim_tool_history, render_tool_history_text

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _normalize_chat_role(role: str) -> Literal["user", "assistant"] | None:
    if role == "user":
        return "user"
    if role == "assistant":
        return "assistant"
    return None


class HistoryController:
    """History operations for SessionState."""

    def __init__(
        self,
        *,
        config: HistoryRuntimeConfig,
        tool_history_budget: int | None = None,
        chat_tokenizer: FastTokenizer | None = None,
        tool_tokenizer: FastTokenizer | None = None,
    ):
        self._config = config
        self._tool_budget = tool_history_budget
        self._chat_tokenizer = chat_tokenizer
        self._tool_tokenizer = tool_tokenizer

    def _sync_mode_storage(self, state: SessionState) -> None:
        if self._config.deploy_chat:
            if state.chat_history_messages is None:
                state.chat_history_messages = []
        else:
            state.chat_history_messages = None

        if self._config.deploy_tool:
            if state.tool_history_turns is None:
                state.tool_history_turns = []
        else:
            state.tool_history_turns = None

    def initialize_mode_state(self, state: SessionState) -> None:
        self._sync_mode_storage(state)

    def _chat_messages(self, state: SessionState) -> list[ChatMessage]:
        messages = state.chat_history_messages
        return messages if messages is not None else []

    def _tool_turns(self, state: SessionState) -> list[HistoryTurn]:
        turns = state.tool_history_turns
        return turns if turns is not None else []

    def _trim_chat_store_eager(self, state: SessionState, *, import_mode: bool = False) -> None:
        if not self._config.deploy_chat:
            return
        if import_mode:
            trim_chat_history(
                state,
                config=self._config,
                chat_tokenizer=self._chat_tokenizer,
                trigger_tokens=self._config.chat_target_tokens,
            )
            return
        trim_chat_history(
            state,
            config=self._config,
            chat_tokenizer=self._chat_tokenizer,
        )

    def _trim_tool_store_eager(self, state: SessionState) -> None:
        if not self._config.deploy_tool or not self._tool_budget:
            return
        trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)

    def _append_chat_message_to_list(self, messages: list[ChatMessage], role: str, content: str) -> None:
        normalized_content = (content or "").strip()
        normalized_role = _normalize_chat_role(role)
        if normalized_role is None or not normalized_content or not self._config.deploy_chat:
            return
        if normalized_role == "user" and messages and messages[-1].role == "user":
            messages[-1].content = f"{messages[-1].content}\n\n{normalized_content}"
            return
        messages.append(ChatMessage(role=normalized_role, content=normalized_content))

    def _append_chat_message(self, state: SessionState, role: str, content: str) -> None:
        self._append_chat_message_to_list(self._chat_messages(state), role, content)

    def _build_imported_chat_messages(self, chat_messages: list[ChatMessage] | None) -> list[ChatMessage]:
        normalized_chat_messages: list[ChatMessage] = []
        for msg in chat_messages or []:
            self._append_chat_message_to_list(normalized_chat_messages, msg.role, msg.content)
        return normalized_chat_messages

    def _set_chat_history_store(self, state: SessionState, chat_messages: list[ChatMessage]) -> None:
        state.chat_history_messages = chat_messages if self._config.deploy_chat else None
        self._trim_chat_store_eager(state, import_mode=True)

    def set_exact_chat_messages(self, state: SessionState, chat_messages: list[ChatMessage]) -> None:
        """Replace chat history with an already-fitted exact message list."""
        state.chat_history_messages = chat_messages if self._config.deploy_chat else None

    def _build_imported_tool_turns(
        self,
        normalized_chat_messages: list[ChatMessage],
        tool_turns: list[HistoryTurn] | None,
    ) -> list[HistoryTurn]:
        source_turns = tool_turns
        if source_turns is None:
            source_turns = [
                HistoryTurn(turn_id=uuid.uuid4().hex, user=msg.content, assistant="")
                for msg in normalized_chat_messages
                if msg.role == "user"
            ]
        return [
            HistoryTurn(turn_id=turn.turn_id, user=turn.user, assistant="")
            for turn in source_turns
            if (turn.user or "").strip()
        ]

    def _set_tool_history_store(
        self,
        state: SessionState,
        normalized_chat_messages: list[ChatMessage],
        tool_turns: list[HistoryTurn] | None,
    ) -> None:
        if not self._config.deploy_tool:
            return
        state.tool_history_turns = self._build_imported_tool_turns(normalized_chat_messages, tool_turns)
        self._trim_tool_store_eager(state)

    def get_text(self, state: SessionState) -> str:
        """Get the transcript view of committed chat history."""
        self._sync_mode_storage(state)
        return render_history(self._chat_messages(state))

    def get_chat_messages(self, state: SessionState) -> list[ChatMessage]:
        """Get a copy of committed chat history messages."""
        self._sync_mode_storage(state)
        return [ChatMessage(role=msg.role, content=msg.content) for msg in self._chat_messages(state)]

    def get_tool_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts from the tool-history store."""
        self._sync_mode_storage(state)
        return get_user_texts(self._tool_turns(state))

    def get_tool_history_text(
        self,
        state: SessionState,
        *,
        max_tokens: int | None = None,
    ) -> str:
        """Get user-only history for the tool model."""
        self._sync_mode_storage(state)
        if self._config.deploy_tool:
            user_texts = get_user_texts(self._tool_turns(state))
            if not user_texts:
                return ""
            if max_tokens is None:
                return "\n".join(user_texts)
            return build_tool_history(
                user_texts,
                max(1, int(max_tokens)),
                self._tool_tokenizer,
                oversize_policy="trim_latest_tail",
            )

        return render_tool_history_text(
            self._tool_turns(state),
            config=self._config,
            max_tokens=max_tokens,
            tool_tokenizer=self._tool_tokenizer,
        )

    def set_mode_histories(
        self,
        state: SessionState,
        *,
        chat_messages: list[ChatMessage] | None = None,
        tool_turns: list[HistoryTurn] | None = None,
    ) -> str:
        """Set imported chat/tool stores and apply import-time trimming."""
        self._sync_mode_storage(state)
        normalized_chat_messages = self._build_imported_chat_messages(chat_messages)
        self._set_chat_history_store(state, normalized_chat_messages)
        self._set_tool_history_store(state, normalized_chat_messages, tool_turns)
        return render_history(self._chat_messages(state))

    def reserve_turn_id(
        self,
        *,
        chat_user_utt: str = "",
        tool_user_utt: str | None = None,
    ) -> str | None:
        """Reserve a stable id for tool-history writes only."""
        tool_user = (tool_user_utt if tool_user_utt is not None else chat_user_utt or "").strip()
        if self._config.deploy_tool and tool_user:
            return uuid.uuid4().hex
        return None

    def append_tool_turn(
        self,
        state: SessionState,
        tool_user_utt: str,
        *,
        turn_id: str | None = None,
    ) -> str | None:
        """Append a user-only tool-history turn exactly once."""
        self._sync_mode_storage(state)
        user = (tool_user_utt or "").strip()
        if not self._config.deploy_tool or not user:
            return turn_id

        tool_turns = self._tool_turns(state)
        if turn_id:
            target = next((t for t in tool_turns if t.turn_id == turn_id), None)
            if target is not None:
                target.user = user
                self._trim_tool_store_eager(state)
                return turn_id

        new_turn_id = turn_id or uuid.uuid4().hex
        tool_turns.append(HistoryTurn(turn_id=new_turn_id, user=user, assistant=""))
        self._trim_tool_store_eager(state)
        return new_turn_id

    def append_chat_response(
        self,
        state: SessionState,
        chat_user_utt: str,
        assistant_text: str,
    ) -> str:
        """Append one chat response as stored user+assistant messages."""
        self._sync_mode_storage(state)
        user = (chat_user_utt or "").strip()
        assistant = (assistant_text or "").strip()
        if not user:
            return render_history(self._chat_messages(state))

        self._append_chat_message(state, "user", user)
        if assistant:
            self._append_chat_message(state, "assistant", assistant)
        self._trim_chat_store_eager(state)
        return render_history(self._chat_messages(state))


__all__ = ["HistoryController"]
