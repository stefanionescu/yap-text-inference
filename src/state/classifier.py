"""Classifier state dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from src.classifier.future import BatchFuture


@dataclass(slots=True)
class RequestItem:
    """A single classification request pending execution."""

    text: str
    future: BatchFuture


@dataclass(slots=True)
class ClassifierModelInfo:
    """Metadata describing the classifier checkpoint and runtime needs."""

    model_id: str
    model_type: str
    max_length: int
    num_labels: int


__all__ = ["RequestItem", "ClassifierModelInfo"]
