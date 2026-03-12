from __future__ import annotations

from tests.suites.integration import test_cancel


def test_cancel_parser_defaults_start_payload_mode_from_tool_deploy(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOY_MODE", "tool")
    monkeypatch.setattr("sys.argv", ["test_cancel.py"])

    args = test_cancel._parse_args()

    assert args.start_payload_mode == "tool-only"


def test_cancel_parser_defaults_start_payload_mode_from_chat_deploy(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOY_MODE", "chat")
    monkeypatch.setattr("sys.argv", ["test_cancel.py"])

    args = test_cancel._parse_args()

    assert args.start_payload_mode == "chat-only"


def test_cancel_parser_keeps_explicit_start_payload_mode_override(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOY_MODE", "tool")
    monkeypatch.setattr("sys.argv", ["test_cancel.py", "--start-payload-mode", "all"])

    args = test_cancel._parse_args()

    assert args.start_payload_mode == "all"
