"""Unit tests for session history accounting invariants."""

from __future__ import annotations

from typing import Any, cast
from src.tokens import count_tokens_tool
import src.tokens.history as history_tokens
import src.handlers.session.history.ops as history_ops
from src.handlers.session.manager import SessionHandler
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.state.session import ChatMessage, HistoryTurn, SessionState
from src.handlers.session.history.settings import HistoryRuntimeConfig
from tests.support.messages.unit import TOOL_HISTORY, CHAT_MESSAGES, ASSISTANT_FIRST_MESSAGES


def _history_config(
    *,
    deploy_chat: bool,
    deploy_tool: bool,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
    default_tool_history_tokens: int | None = None,
) -> HistoryRuntimeConfig:
    return HistoryRuntimeConfig(
        deploy_chat=deploy_chat,
        deploy_tool=deploy_tool,
        chat_trigger_tokens=chat_trigger_tokens,
        chat_target_tokens=chat_target_tokens,
        default_tool_history_tokens=default_tool_history_tokens,
    )


def _make_state(handler: SessionHandler) -> SessionState:
    state = SessionState(meta={})
    handler.initialize_session(state)
    return state


def _build_chat_only_handler(
    *,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
    tokenizer: Any | None = None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        chat_tokenizer=cast(Any, tokenizer),
        history_config=_history_config(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=chat_trigger_tokens,
            chat_target_tokens=chat_target_tokens,
        ),
    )


def _build_tool_only_handler(
    *,
    tool_history_budget: int = 10,
    tool_input_budget: int | None = None,
    tokenizer: Any | None = None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_history_budget=tool_history_budget,
        tool_input_budget=tool_input_budget,
        tool_tokenizer=cast(Any, tokenizer),
        history_config=_history_config(
            deploy_chat=False,
            deploy_tool=True,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
        ),
    )


def _build_dual_mode_handler(
    *,
    tool_history_budget: int = 10,
    tool_input_budget: int | None = None,
    tokenizer: Any | None = None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_history_budget=tool_history_budget,
        tool_input_budget=tool_input_budget,
        chat_tokenizer=cast(Any, tokenizer),
        tool_tokenizer=cast(Any, tokenizer),
        history_config=_history_config(
            deploy_chat=True,
            deploy_tool=True,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
        ),
    )


def test_append_chat_turn_stores_user_and_assistant_as_separate_messages() -> None:
    with use_local_tokenizers() as tokenizer:
        session_handler = _build_chat_only_handler(tokenizer=tokenizer)
        state = _make_state(session_handler)

        turn_id = session_handler.reserve_history_turn_id(state, "hello")
        assert turn_id is None

        session_handler.append_chat_turn(state, "hello", "world", turn_id=turn_id)
        rendered = session_handler._history.get_text(state)

        assert state.chat_history_messages is not None
        assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
            ("user", "hello"),
            ("assistant", "world"),
        ]
        assert "User: hello" in rendered
        assert "Assistant: world" in rendered


def test_set_mode_histories_keeps_expected_message_count() -> None:
    with use_local_tokenizers():
        session_handler = _build_chat_only_handler()
        state = _make_state(session_handler)

        messages = CHAT_MESSAGES[:3] + [ChatMessage(role="assistant", content="reply")]

        rendered = session_handler._history.set_mode_histories(state, chat_messages=messages)

        assert "User: hello can you help me plan a trip to lisbon next week" in rendered
        assert "Assistant: reply" in rendered
        assert state.chat_history_messages is not None
        assert len(state.chat_history_messages) == 4


def test_append_chat_turn_merges_consecutive_users_in_storage() -> None:
    with use_local_tokenizers():
        handler = _build_chat_only_handler()
        state = _make_state(handler)
        state.chat_history_messages = [ChatMessage(role="user", content="seed")]

        handler.append_chat_turn(state, "follow up", "reply")

        assert state.chat_history_messages is not None
        assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
            ("user", "seed\n\nfollow up"),
            ("assistant", "reply"),
        ]


def test_render_tool_history_text_keeps_latest_line_when_single_line_exceeds_budget() -> None:
    with use_local_tokenizers() as tokenizer:
        config = _history_config(deploy_chat=False, deploy_tool=True)
        turns = [HistoryTurn(turn_id="t1", user=TOOL_HISTORY[-1], assistant="")]
        rendered = history_ops.render_tool_history_text(
            turns,
            config=config,
            max_tokens=4,
            tool_tokenizer=tokenizer,
        )
        assert rendered == "weather notes for lisbon"
        assert count_tokens_tool(rendered) == 4


def test_render_tool_history_text_uses_raw_user_lines() -> None:
    with use_local_tokenizers() as tokenizer:
        config = _history_config(deploy_chat=False, deploy_tool=True)
        turns = [
            HistoryTurn(turn_id="t1", user=TOOL_HISTORY[0], assistant="assistant one"),
            HistoryTurn(turn_id="t2", user=TOOL_HISTORY[1], assistant="assistant two"),
        ]
        rendered = history_ops.render_tool_history_text(
            turns,
            config=config,
            max_tokens=40,
            tool_tokenizer=tokenizer,
        )
        assert rendered == "\n".join(TOOL_HISTORY[:2])
        assert "User:" not in rendered
        assert "Assistant:" not in rendered


def test_tool_only_mode_keeps_chat_history_inactive() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=20, tokenizer=tokenizer)
        state = _make_state(handler)

        assert state.chat_history_messages is None
        assert state.tool_history_turns == []

        turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt="show me this")
        tool_user, tool_history = handler.prepare_tool_turn(state, "show me this", turn_id=turn_id)

        assert tool_user == "show me this"
        assert tool_history == ""
        assert state.chat_history_messages is None
        assert state.tool_history_turns is not None
        assert [(turn.turn_id, turn.user) for turn in state.tool_history_turns] == [(turn_id, "show me this")]


def test_chat_only_mode_keeps_tool_history_inactive() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_only_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        assert state.chat_history_messages == []
        assert state.tool_history_turns is None

        handler.append_chat_turn(state, "hello", "world")

        assert state.chat_history_messages is not None
        assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
            ("user", "hello"),
            ("assistant", "world"),
        ]
        assert state.tool_history_turns is None


def test_reserve_history_turn_id_does_not_mutate_stores() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_dual_mode_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        turn_id = handler.reserve_history_turn_id(state, "hello", tool_user_utt="hello")

        assert turn_id is not None
        assert state.chat_history_messages == []
        assert state.tool_history_turns == []


def test_prepare_tool_turn_dual_mode_appends_once_and_chat_commit_does_not_duplicate_tool_history() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_dual_mode_handler(tool_history_budget=20, tool_input_budget=20, tokenizer=tokenizer)
        state = _make_state(handler)

        seed_turn_id = handler.reserve_history_turn_id(state, "alpha one", tool_user_utt="alpha one")
        seed_tool_user, seed_tool_history = handler.prepare_tool_turn(state, "alpha one", turn_id=seed_turn_id)
        assert seed_tool_user == "alpha one"
        assert seed_tool_history == ""

        turn_id = handler.reserve_history_turn_id(state, "bravo two", tool_user_utt="bravo two")
        prepared_user, tool_history = handler.prepare_tool_turn(state, "bravo two", turn_id=turn_id)

        assert prepared_user == "bravo two"
        assert tool_history == "alpha one"
        assert state.tool_history_turns is not None
        assert [(turn.turn_id, turn.user) for turn in state.tool_history_turns] == [
            (seed_turn_id, "alpha one"),
            (turn_id, "bravo two"),
        ]

        handler.append_chat_turn(state, "bravo two", "assistant reply", turn_id=turn_id)

        assert state.tool_history_turns is not None
        assert [(turn.turn_id, turn.user) for turn in state.tool_history_turns] == [
            (seed_turn_id, "alpha one"),
            (turn_id, "bravo two"),
        ]
        assert state.chat_history_messages is not None
        assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
            ("user", "bravo two"),
            ("assistant", "assistant reply"),
        ]


def test_prepare_tool_turn_fits_exact_combined_input_before_backend_call() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=20, tool_input_budget=4, tokenizer=tokenizer)
        state = _make_state(handler)

        seed_turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt="check the calendar")
        handler.prepare_tool_turn(state, "check the calendar", turn_id=seed_turn_id)

        turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt="show the booking confirmation")
        tool_user, tool_history = handler.prepare_tool_turn(state, "show the booking confirmation", turn_id=turn_id)

        combined = "\n".join([part for part in [tool_history, tool_user] if part])
        assert tool_history == ""
        assert tool_user == "show the booking confirmation"
        assert count_tokens_tool(combined) <= 4


def test_prepare_tool_turn_trims_current_user_tail_when_history_is_exhausted() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=20, tool_input_budget=4, tokenizer=tokenizer)
        state = _make_state(handler)

        user_text = "check the calendar for next tuesday flight times"
        turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt=user_text)
        tool_user, tool_history = handler.prepare_tool_turn(state, user_text, turn_id=turn_id)

        assert tool_history == ""
        assert tool_user == "next tuesday flight times"
        assert state.tool_history_turns is not None
        assert [(turn.turn_id, turn.user) for turn in state.tool_history_turns] == [
            (turn_id, "next tuesday flight times")
        ]


def test_trim_history_tool_only_drops_old_turns() -> None:
    with use_local_tokenizers():
        state = SessionState(meta={})
        state.tool_history_turns = [
            HistoryTurn(turn_id=f"t{i}", user=f"word{i} extra{i} more{i}", assistant="") for i in range(5)
        ]
        history_ops.trim_tool_history(state, 6)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) < 5
        assert state.tool_history_turns[-1].turn_id == "t4"


def test_trim_history_tool_only_keeps_single_oversized_last_turn() -> None:
    with use_local_tokenizers() as tokenizer:
        state = SessionState(meta={})
        long_text = "check the calendar for next tuesday flight times"
        state.tool_history_turns = [HistoryTurn(turn_id="t1", user=long_text, assistant="")]
        history_ops.trim_tool_history(state, 3, tool_tokenizer=tokenizer)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        assert state.tool_history_turns[0].user == "tuesday flight times"


def test_trim_history_tool_only_noop_when_under_budget() -> None:
    with use_local_tokenizers():
        state = SessionState(meta={})
        state.tool_history_turns = [
            HistoryTurn(turn_id="t1", user="hi", assistant=""),
            HistoryTurn(turn_id="t2", user="hello", assistant=""),
        ]
        history_ops.trim_tool_history(state, 100)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 2


def test_prepare_tool_turn_retention_budget_trims_store_eagerly() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=6, tool_input_budget=20, tokenizer=tokenizer)
        state = _make_state(handler)

        for i in range(6):
            turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt=f"word{i} extra{i} more{i}")
            handler.prepare_tool_turn(state, f"word{i} extra{i} more{i}", turn_id=turn_id)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) < 6
        rendered = handler._history.get_tool_history_text(state)
        assert count_tokens_tool(rendered) <= 6


def test_append_chat_turn_trims_chat_history_eagerly() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_only_handler(chat_trigger_tokens=10, chat_target_tokens=6, tokenizer=tokenizer)
        state = _make_state(handler)

        turns = [
            ("hello how are you", "great"),
            ("alpha bravo charlie", "one two"),
            ("hello world", "three four"),
            ("u1 u2 u3", "a1 a2"),
        ]
        for user_text, assistant_text in turns:
            handler.append_chat_turn(state, user_text, assistant_text)

        assert state.chat_history_messages is not None
        assert len(state.chat_history_messages) < len(turns) * 2
        assert state.chat_history_messages[0].role == "user"
        assert len(state.chat_history_messages) % 2 == 0


def test_append_chat_turn_trim_preserves_complete_recent_turns() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_only_handler(chat_trigger_tokens=8, chat_target_tokens=4, tokenizer=tokenizer)
        state = _make_state(handler)

        handler.append_chat_turn(state, "hello how are you", "great")
        handler.append_chat_turn(state, "alpha bravo charlie", "one two three")

        assert state.chat_history_messages is not None
        assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
            ("user", "alpha bravo charlie"),
            ("assistant", "one two three"),
        ]


def test_trim_chat_history_preserves_assistant_first_groups_as_whole_units() -> None:
    with use_local_tokenizers() as tokenizer:
        state = SessionState(meta={})
        state.chat_history_messages = list(ASSISTANT_FIRST_MESSAGES)

        history_ops.trim_chat_history(
            state,
            config=_history_config(
                deploy_chat=True,
                deploy_tool=False,
                chat_trigger_tokens=60,
                chat_target_tokens=40,
            ),
            chat_tokenizer=tokenizer,
        )

        assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[-2:]


def test_get_tool_history_text_returns_full_store_contents() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=30, tool_input_budget=30, tokenizer=tokenizer)
        state = _make_state(handler)

        for text in ("alpha one", "bravo two", "charlie three"):
            turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt=text)
            handler.prepare_tool_turn(state, text, turn_id=turn_id)

        assert handler._history.get_tool_history_text(state) == "alpha one\nbravo two\ncharlie three"


def test_prepare_tool_turn_tool_only_keeps_single_oversized_turn_in_store() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_only_handler(tool_history_budget=3, tool_input_budget=20, tokenizer=tokenizer)
        state = _make_state(handler)

        long_text = "check the calendar for next tuesday flight times"
        turn_id = handler.reserve_history_turn_id(state, "", tool_user_utt=long_text)
        tool_user, _ = handler.prepare_tool_turn(state, long_text, turn_id=turn_id)

        assert tool_user == long_text
        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        assert state.tool_history_turns[0].user == "tuesday flight times"
        assert handler._history.get_tool_history_text(state) == "tuesday flight times"


class _SpecialAwareTokenizer:
    def count(self, text: str, *, add_special_tokens: bool = False) -> int:
        if not text.strip():
            return 0
        total = len(text.split())
        if add_special_tokens:
            total += 2
        return total

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        tokens = text.split()
        if max_tokens <= 0:
            return ""
        if len(tokens) <= max_tokens:
            return text
        kept = tokens[:max_tokens] if keep == "start" else tokens[-max_tokens:]
        return " ".join(kept)

    def encode_ids(self, text: str) -> list[int]:
        return list(range(len(text.split())))


def test_build_tool_history_accounts_for_special_tokens() -> None:
    tokenizer = cast(Any, _SpecialAwareTokenizer())

    kept = history_tokens.build_tool_history(
        ["one two", "three four"],
        budget=5,
        tool_tokenizer=tokenizer,
    )
    assert kept == "three four"


def test_build_tool_history_trims_single_oversized_line_with_special_tokens() -> None:
    tokenizer = cast(Any, _SpecialAwareTokenizer())

    kept = history_tokens.build_tool_history(
        ["one two"],
        budget=3,
        tool_tokenizer=tokenizer,
    )
    assert kept == "two"
