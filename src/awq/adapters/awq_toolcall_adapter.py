#!/usr/bin/env python3
"""Toolcall-specific helpers for AWQ quantization."""

from __future__ import annotations

import os
from typing import Any

TOOLCALL_MODEL_MARKERS = (
    "madeagents/hammer",
    "hammer2.1",
    "hammer_model",
)

_TOOLCALL_DEFAULT_TOTAL_LEN = 3010  # Fallback if env vars are missing


def _read_int_env(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_model_id(model_id: str) -> str:
    return model_id.strip().lower()


def is_toolcall_model(model_id: str) -> bool:
    norm = normalize_model_id(model_id)
    return any(marker in norm for marker in TOOLCALL_MODEL_MARKERS)


def compute_toolcall_calibration_seqlen(requested: int) -> int:
    tool_max_len = _read_int_env("TOOL_MAX_LEN")
    tool_max_out = _read_int_env("TOOL_MAX_OUT")

    total = 0
    if tool_max_len is not None:
        total += tool_max_len
    if tool_max_out is not None:
        total += tool_max_out

    if total > 0:
        return max(requested, total)

    return max(requested, _TOOLCALL_DEFAULT_TOTAL_LEN)


def apply_toolcall_awq_adapters(target_seqlen: int) -> None:
    _apply_toolcall_catcher_patch()
    _apply_toolcall_qwen_patch()
    _apply_toolcall_quantizer_patch(target_seqlen)


def _iter_catcher_classes(quantizer_module: Any) -> list[type[Any]]:
    classes: list[type[Any]] = []
    for attr_name in dir(quantizer_module):
        if "catch" not in attr_name.lower():
            continue
        attr_value = getattr(quantizer_module, attr_name, None)
        if isinstance(attr_value, type):
            classes.append(attr_value)
    return classes


def _apply_toolcall_catcher_patch() -> None:
    try:
        from awq.quantize import quantizer  # type: ignore
    except Exception as exc:
        print(f"[awq] Toolcall patch skipped: unable to import AutoAWQ quantizer ({exc})")
        return

    catcher_classes = _iter_catcher_classes(quantizer)
    if not catcher_classes:
        print("[awq] Toolcall patch skipped: AutoAWQ catcher helper not found")
        return

    for catcher_cls in catcher_classes:
        if getattr(catcher_cls, "_toolcall_attribute_proxy_patch", False):
            continue

        original_init = catcher_cls.__init__
        original_getattr = getattr(catcher_cls, "__getattr__", None)

        def patched_init(self, module, *args, _orig_init=original_init, **kwargs):  # type: ignore[override]
            _orig_init(self, module, *args, **kwargs)
            object.__setattr__(self, "_toolcall_wrapped_module", module)
            if hasattr(module, "attention_type"):
                object.__setattr__(self, "attention_type", module.attention_type)

        def patched_getattr(self, name, _orig_getattr=original_getattr):  # type: ignore[override]
            if name == "_toolcall_wrapped_module":
                raise AttributeError(name)

            if _orig_getattr is not None:
                try:
                    return _orig_getattr(self, name)  # type: ignore[misc]
                except AttributeError:
                    pass

            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                pass

            try:
                wrapped = object.__getattribute__(self, "_toolcall_wrapped_module")
            except AttributeError:
                raise AttributeError(name) from None

            try:
                return getattr(wrapped, name)
            except AttributeError:
                raise AttributeError(name) from None

        catcher_cls.__init__ = patched_init  # type: ignore[assignment]
        catcher_cls.__getattr__ = patched_getattr  # type: ignore[assignment]
        catcher_cls._toolcall_attribute_proxy_patch = True
        print(f"[awq] Applied Toolcall-specific catcher patch ({catcher_cls.__name__})")


def _apply_toolcall_qwen_patch() -> None:
    try:
        from transformers.models.qwen2.modeling_qwen2 import Qwen2Model  # type: ignore
    except Exception as exc:
        print(f"[awq] Toolcall patch skipped: unable to import Qwen2Model ({exc})")
        return

    if getattr(Qwen2Model, "_toolcall_attention_type_patch", False):
        return

    original_forward = Qwen2Model.forward

    def patched_forward(self, *args, **kwargs):  # type: ignore[override]
        try:
            layer_types = getattr(self.config, "layer_types", None)
            if layer_types is not None:
                for idx, decoder_layer in enumerate(self.layers[: self.config.num_hidden_layers]):
                    if hasattr(decoder_layer, "attention_type"):
                        continue
                    try:
                        attention_type = layer_types[idx]
                    except Exception:
                        attention_type = "full_attention"
                    decoder_layer.attention_type = attention_type
        except Exception:
            pass
        return original_forward(self, *args, **kwargs)

    Qwen2Model.forward = patched_forward  # type: ignore[assignment]
    Qwen2Model._toolcall_attention_type_patch = True
    print("[awq] Applied Toolcall-specific Qwen2 attention patch")


def _truncate_sequence_like(obj: Any, max_len: int | None) -> Any:
    if max_len is None:
        return obj

    try:
        import torch

        if isinstance(obj, torch.Tensor):
            if obj.dim() >= 1 and obj.size(-1) > max_len:
                return obj[..., :max_len]
            return obj
    except Exception:
        pass

    if isinstance(obj, list | tuple) and len(obj) > max_len:
        return obj[:max_len]

    return obj


def _apply_toolcall_quantizer_patch(target_seqlen: int) -> None:
    try:
        from awq.quantize import quantizer  # type: ignore
        AwqQuantizer = quantizer.AwqQuantizer
    except Exception as exc:
        print(f"[awq] Toolcall patch skipped: unable to import AwqQuantizer ({exc})")
        return

    AwqQuantizer._toolcall_default_target_seqlen = int(target_seqlen)

    if getattr(AwqQuantizer, "_toolcall_truncate_patch", False):
        return

    original_init_quant = AwqQuantizer.init_quant

    def patched_init_quant(self, *args, **kwargs):  # type: ignore[override]
        target_len = getattr(
            self,
            "_toolcall_target_seqlen",
            getattr(AwqQuantizer, "_toolcall_default_target_seqlen", None),
        )
        self._toolcall_target_seqlen = target_len

        original_forward = self.model.forward

        if target_len is not None:

            def capped_forward(*fargs, **fkwargs):  # type: ignore[override]
                new_args = list(fargs)
                if new_args:
                    new_args[0] = _truncate_sequence_like(new_args[0], target_len)
                new_kwargs = dict(fkwargs)
                for key in ("input_ids", "attention_mask", "position_ids", "cache_position"):
                    if key in new_kwargs:
                        new_kwargs[key] = _truncate_sequence_like(new_kwargs[key], target_len)
                return original_forward(*new_args, **new_kwargs)

            wrapped_forward = capped_forward
        else:

            def wrapped_forward(*fargs, **fkwargs):  # type: ignore[override]
                return original_forward(*fargs, **fkwargs)

        self.model.forward = wrapped_forward
        try:
            result = original_init_quant(self, *args, **kwargs)
        finally:
            self.model.forward = original_forward

        return result

    AwqQuantizer.init_quant = patched_init_quant  # type: ignore[assignment]
    AwqQuantizer._toolcall_truncate_patch = True
    print("[awq] Applied Toolcall-specific quantizer truncation patch")


__all__ = [
    "apply_toolcall_awq_adapters",
    "compute_toolcall_calibration_seqlen",
    "is_toolcall_model",
]


