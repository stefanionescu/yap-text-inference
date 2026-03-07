"""History orchestration for SessionState with mode-aware storage."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from .settings import HistoryRuntimeConfig
from .token_counting import build_tool_history
from src.state.session import HistoryTurn, SessionState
from .ops import get_user_texts, render_history, trim_chat_history, trim_tool_history, render_tool_history_text

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


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
        """Keep only active history stores populated for the current deploy mode."""
        if self._config.deploy_chat:
            if state.history_turns is None:
                state.history_turns = []
        else:
            state.history_turns = None

        if self._config.deploy_tool:
            if state.tool_history_turns is None:
                state.tool_history_turns = []
        else:
            state.tool_history_turns = None

    def initialize_mode_state(self, state: SessionState) -> None:
        """Initialize/normalize history stores for deployment mode."""
        self._sync_mode_storage(state)

    def _chat_turns(self, state: SessionState) -> list[HistoryTurn]:
        turns = state.history_turns
        return turns if turns is not None else []

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

    def get_text(self, state: SessionState) -> str:
        """Get full rendered history (User + Assistant turns)."""
        self._sync_mode_storage(state)
        return render_history(self._chat_turns(state))

    def get_turns(self, state: SessionState, *, include_latest: bool = True) -> list[HistoryTurn]:
        """Get a copy of chat history turns."""
        self._sync_mode_storage(state)
        turns = self._chat_turns(state)
        if not include_latest and turns:
            turns = turns[:-1]
        return [HistoryTurn(turn_id=t.turn_id, user=t.user, assistant=t.assistant) for t in turns]

    def get_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts for the appropriate deploy mode."""
        self._sync_mode_storage(state)
        if self._config.deploy_tool:
            return get_user_texts(self._tool_turns(state))
        return get_user_texts(self._chat_turns(state))

    def get_tool_history_text(
        self,
        state: SessionState,
        *,
        max_tokens: int | None = None,
        include_latest: bool = True,
    ) -> str:
        """Get user-only history for the tool model."""
        self._sync_mode_storage(state)
        if self._config.deploy_tool:
            tool_turns = self._tool_turns(state)
            if not include_latest and tool_turns:
                tool_turns = tool_turns[:-1]
            user_texts = get_user_texts(tool_turns)
            if not user_texts:
                return ""
            if max_tokens is None:
                return "\n".join(user_texts)
            return build_tool_history(user_texts, max(1, int(max_tokens)), self._tool_tokenizer)

        chat_turns = self._chat_turns(state)
        if not include_latest and chat_turns:
            chat_turns = chat_turns[:-1]
        return render_tool_history_text(
            chat_turns,
            config=self._config,
            max_tokens=max_tokens,
            tool_tokenizer=self._tool_tokenizer,
        )

    def set_mode_turns(
        self,
        state: SessionState,
        *,
        chat_turns: list[HistoryTurn] | None = None,
        tool_turns: list[HistoryTurn] | None = None,
    ) -> str:
        """Set chat/tool histories independently and apply import-time trimming."""
        self._sync_mode_storage(state)
        normalized_chat_turns = chat_turns or []
        if self._config.deploy_chat:
            state.history_turns = normalized_chat_turns
        else:
            state.history_turns = None

        self._trim_chat_store_eager(state, import_mode=True)

        if self._config.deploy_tool:
            source_turns = tool_turns if tool_turns is not None else normalized_chat_turns
            state.tool_history_turns = [
                HistoryTurn(turn_id=t.turn_id, user=t.user, assistant="")
                for t in source_turns
                if (t.user or "").strip()
            ]
            self._trim_tool_store_eager(state)
        return render_history(self._chat_turns(state))

    def append_user_turn(
        self,
        state: SessionState,
        chat_user_utt: str,
        *,
        tool_user_utt: str | None = None,
    ) -> str | None:
        self._sync_mode_storage(state)
        chat_user = (chat_user_utt or "").strip()
        tool_user = (tool_user_utt if tool_user_utt is not None else chat_user_utt or "").strip()
        if not chat_user and not tool_user:
            return None

        turn_id: str | None = None
        if self._config.deploy_chat and chat_user:
            turn_id = uuid.uuid4().hex
            self._chat_turns(state).append(HistoryTurn(turn_id=turn_id, user=chat_user, assistant=""))
            self._trim_chat_store_eager(state)

        if self._config.deploy_tool and tool_user:
            if turn_id is None:
                turn_id = uuid.uuid4().hex
            self._tool_turns(state).append(HistoryTurn(turn_id=turn_id, user=tool_user, assistant=""))
            self._trim_tool_store_eager(state)
        return turn_id

    def append_turn(
        self,
        state: SessionState,
        chat_user_utt: str,
        assistant_text: str,
        *,
        turn_id: str | None = None,
    ) -> str:
        self._sync_mode_storage(state)
        user = (chat_user_utt or "").strip()
        assistant = assistant_text or ""

        chat_turns = self._chat_turns(state)
        if turn_id and self._config.deploy_chat:
            target = next((t for t in chat_turns if t.turn_id == turn_id), None)
            if target is not None:
                if assistant:
                    target.assistant = assistant
                self._trim_chat_store_eager(state)
                return render_history(chat_turns)

        if not user and not assistant:
            return render_history(chat_turns)

        new_turn_id = turn_id or uuid.uuid4().hex
        if self._config.deploy_chat:
            chat_turns.append(
                HistoryTurn(
                    turn_id=new_turn_id,
                    user=user,
                    assistant=assistant,
                )
            )
        self._trim_chat_store_eager(state)

        if user and self._config.deploy_tool:
            self._tool_turns(state).append(HistoryTurn(turn_id=new_turn_id, user=user, assistant=""))
            self._trim_tool_store_eager(state)
        return render_history(chat_turns)


__all__ = ["HistoryController"]
