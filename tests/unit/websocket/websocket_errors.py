"""Unit tests for websocket error payload building."""

from __future__ import annotations

from src.handlers.websocket.errors import build_error_payload


def test_build_error_payload_basic() -> None:
    result = build_error_payload("err_code", "something went wrong")
    assert result["code"] == "err_code"
    assert result["message"] == "something went wrong"
    assert result["details"] == {}


def test_build_error_payload_with_details() -> None:
    result = build_error_payload("err", "msg", details={"field": "value"})
    assert result["details"]["field"] == "value"


def test_build_error_payload_with_reason_code() -> None:
    result = build_error_payload("err", "msg", reason_code="rate_limited")
    assert result["details"]["reason_code"] == "rate_limited"


def test_build_error_payload_reason_code_does_not_overwrite() -> None:
    result = build_error_payload(
        "err",
        "msg",
        details={"reason_code": "existing"},
        reason_code="new",
    )
    # setdefault preserves existing
    assert result["details"]["reason_code"] == "existing"
