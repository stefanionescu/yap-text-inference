"""Helpers for emitting SNAC token metadata during streaming."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from server.config import settings


@dataclass
class SnacTokenRecord:
    token_id: int
    channel: int
    code: int
    frame_index: int
    frame_offset: int
    sequence_index: int


class SnacTokenEmitter:
    """Tracks SNAC token metadata for optional downstream emission."""

    def __init__(self):
        self.code_offset = settings.code_offset
        self.code_size = settings.code_size
        self.frame_size = settings.frame_substreams
        self.audio_token_idx = 0

    def observe(self, token_ids: Iterable[int]) -> list[dict[str, int]]:
        records: list[dict[str, int]] = []
        for token_id in token_ids:
            record = self._record_for_token(int(token_id))
            if record is None:
                continue
            records.append(
                {
                    "token_id": record.token_id,
                    "channel": record.channel,
                    "code": record.code,
                    "frame_index": record.frame_index,
                    "frame_offset": record.frame_offset,
                    "sequence_index": record.sequence_index,
                }
            )
        return records

    def _record_for_token(self, token_id: int) -> SnacTokenRecord | None:
        rel = token_id - self.code_offset
        if rel < 0:
            return None
        channel = rel // self.code_size
        if channel < 0 or channel >= self.frame_size:
            return None
        code = rel % self.code_size
        frame_index = self.audio_token_idx // self.frame_size
        frame_offset = self.audio_token_idx % self.frame_size
        seq_idx = self.audio_token_idx
        self.audio_token_idx += 1
        return SnacTokenRecord(token_id, channel, code, frame_index, frame_offset, seq_idx)
