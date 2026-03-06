"""Unit tests for tool result parsing utilities."""

from __future__ import annotations

from src.execution.tool.parser import parse_tool_result, _strip_code_fences


def test_strip_code_fences_removes_leading_json_fence() -> None:
    assert _strip_code_fences("```json\n[]\n```") == "[]"


def test_strip_code_fences_removes_leading_bare_fence() -> None:
    assert _strip_code_fences("```\n[]\n```") == "[]"


def test_strip_code_fences_removes_trailing_stuck_fence() -> None:
    assert _strip_code_fences("[]```") == "[]"


def test_strip_code_fences_removes_trailing_newline_fence() -> None:
    assert _strip_code_fences('[{"name":"x"}]\n```') == '[{"name":"x"}]'


def test_strip_code_fences_noop_when_no_fences() -> None:
    assert _strip_code_fences("[]") == "[]"
    assert _strip_code_fences('[{"name":"x"}]') == '[{"name":"x"}]'


def test_parse_tool_result_none_input() -> None:
    raw, is_tool = parse_tool_result(None)
    assert raw is None
    assert is_tool is False


def test_parse_tool_result_empty_dict() -> None:
    raw, is_tool = parse_tool_result({})
    assert raw is None
    assert is_tool is False


def test_parse_tool_result_empty_list_json() -> None:
    raw, is_tool = parse_tool_result({"text": "[]"})
    assert raw == []
    assert is_tool is False


def test_parse_tool_result_tool_call_present() -> None:
    raw, is_tool = parse_tool_result({"text": '[{"name":"take_screenshot"}]'})
    assert raw == [{"name": "take_screenshot"}]
    assert is_tool is True


def test_parse_tool_result_code_fenced_json() -> None:
    raw, is_tool = parse_tool_result({"text": '```json\n[{"name":"x"}]\n```'})
    assert raw == [{"name": "x"}]
    assert is_tool is True


def test_parse_tool_result_malformed_json() -> None:
    raw, is_tool = parse_tool_result({"text": "not json at all"})
    assert raw == "not json at all"
    assert is_tool is False


def test_parse_tool_result_empty_string_after_fence_strip() -> None:
    raw, is_tool = parse_tool_result({"text": "```json\n\n```"})
    assert raw is None
    assert is_tool is False
