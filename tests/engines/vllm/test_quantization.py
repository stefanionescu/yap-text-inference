"""Tests for quantization metadata sanitization helpers."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

os.environ.setdefault("MAX_CONCURRENT_CONNECTIONS", "32")
os.environ.setdefault("TEXT_API_KEY", "test-key")
os.environ.setdefault("CHAT_MODEL", "ArliAI/Qwen3-30B-A3B-ArliAI-RpR-v4-Fast")
os.environ.setdefault("DEPLOY_MODE", "chat")

from tests.helpers.setup import setup_repo_path

setup_repo_path()

from src.engines.vllm.quantization import (
    sanitize_quantization_metadata,
    strip_unsupported_quant_fields,
)


def test_strip_unsupported_quant_fields_removes_nested_values():
    payload = {
        "quantization_config": {
            "scale_dtype": "float32",
            "inner": {"zp_dtype": "int32", "keep": 42},
        },
        "list": [
            {"scale_dtype": "bfloat16", "other": "ok"},
            "noop",
        ],
    }

    changed = strip_unsupported_quant_fields(payload)

    assert changed is True
    assert "scale_dtype" not in payload["quantization_config"]
    assert "zp_dtype" not in payload["quantization_config"]["inner"]
    assert "scale_dtype" not in payload["list"][0]
    assert payload["quantization_config"]["inner"]["keep"] == 42


def test_strip_unsupported_quant_fields_noop_when_missing():
    payload = {"quantization_config": {"keep": "value"}}

    changed = strip_unsupported_quant_fields(payload)

    assert changed is False
    assert payload == {"quantization_config": {"keep": "value"}}


def test_sanitize_quantization_metadata_rewrites_local_files(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"quantization_config": {"scale_dtype": "float32", "foo": 1}}),
        encoding="utf-8",
    )

    sanitize_quantization_metadata(str(tmp_path))

    rewritten = json.loads(config_path.read_text(encoding="utf-8"))
    assert rewritten == {"quantization_config": {"foo": 1}}
