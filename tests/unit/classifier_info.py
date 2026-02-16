"""Unit tests for classifier model metadata and token-limit defaults."""

from __future__ import annotations

import src.classifier.info as classifier_info


class _DummyConfig:
    def __init__(self, model_type: str, num_labels: int = 2) -> None:
        self.model_type = model_type
        self.num_labels = num_labels


def test_build_model_info_uses_longformer_default_when_not_overridden(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier_info.AutoConfig,
        "from_pretrained",
        lambda *_args, **_kwargs: _DummyConfig("longformer", num_labels=3),
    )

    info = classifier_info.build_model_info("dummy-model", max_length=None)

    assert info.model_type == "longformer"
    assert info.max_length == 1536
    assert info.num_labels == 3


def test_build_model_info_uses_bert_default_when_not_overridden(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier_info.AutoConfig,
        "from_pretrained",
        lambda *_args, **_kwargs: _DummyConfig("modernbert", num_labels=2),
    )

    info = classifier_info.build_model_info("dummy-model", max_length=None)

    assert info.model_type == "bert"
    assert info.max_length == 512


def test_build_model_info_treats_roberta_family_as_bert_path(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier_info.AutoConfig,
        "from_pretrained",
        lambda *_args, **_kwargs: _DummyConfig("roberta", num_labels=2),
    )

    info = classifier_info.build_model_info("dummy-model", max_length=None)

    assert info.model_type == "bert"
    assert info.max_length == 512


def test_build_model_info_respects_max_length_override(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier_info.AutoConfig,
        "from_pretrained",
        lambda *_args, **_kwargs: _DummyConfig("longformer", num_labels=2),
    )

    info = classifier_info.build_model_info("dummy-model", max_length=1024)

    assert info.model_type == "longformer"
    assert info.max_length == 1024


def test_resolve_history_token_limit_clamps_to_max_length() -> None:
    assert classifier_info.resolve_history_token_limit(max_length=512, history_tokens=None) == 512
    assert classifier_info.resolve_history_token_limit(max_length=512, history_tokens=700) == 512
    assert classifier_info.resolve_history_token_limit(max_length=512, history_tokens=300) == 300
