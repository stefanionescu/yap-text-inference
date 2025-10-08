#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any

HAMMER_MODEL_MARKERS = (
    "madeagents/hammer",
    "hammer2.1",
    "hammer_model",
)


def file_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False


def is_awq_dir(path: str) -> bool:
    # Heuristics: common files saved by AutoAWQ
    candidates = [
        os.path.join(path, "awq_config.json"),
        os.path.join(path, "quant_config.json"),
        os.path.join(path, "model.safetensors"),  # presence indicates saved model
    ]
    for cand in candidates:
        if file_exists(cand):
            return True
    return False


def normalize_model_id(model_id: str) -> str:
    return model_id.strip().lower()


def is_hammer_model(model_id: str) -> bool:
    norm = normalize_model_id(model_id)
    return any(marker in norm for marker in HAMMER_MODEL_MARKERS)


def apply_hammer_awq_patches() -> None:
    try:
        from awq.quantize import quantizer  # type: ignore
    except Exception as exc:
        print(f"[awq] Hammer patch skipped: unable to import AutoAWQ quantizer ({exc})")
        return

    catcher_cls = getattr(quantizer, "Catcher", None)
    if catcher_cls is None:
        print("[awq] Hammer patch skipped: AutoAWQ Catcher helper not found")
        return

    if getattr(catcher_cls, "_hammer_attribute_proxy_patch", False):
        return

    original_init = catcher_cls.__init__
    original_getattr = getattr(catcher_cls, "__getattr__", None)

    def patched_init(self, module, *args, **kwargs):  # type: ignore[override]
        original_init(self, module, *args, **kwargs)
        object.__setattr__(self, "_hammer_wrapped_module", module)
        if hasattr(module, "attention_type"):
            object.__setattr__(self, "attention_type", getattr(module, "attention_type"))

    def patched_getattr(self, name):  # type: ignore[override]
        if name == "_hammer_wrapped_module":
            raise AttributeError(name)

        if original_getattr is not None:
            try:
                return original_getattr(self, name)  # type: ignore[misc]
            except AttributeError:
                pass

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            pass

        try:
            wrapped = object.__getattribute__(self, "_hammer_wrapped_module")
        except AttributeError:
            raise AttributeError(name) from None

        try:
            return getattr(wrapped, name)
        except AttributeError:
            raise AttributeError(name) from None

    catcher_cls.__init__ = patched_init  # type: ignore[assignment]
    catcher_cls.__getattr__ = patched_getattr  # type: ignore[assignment]
    setattr(catcher_cls, "_hammer_attribute_proxy_patch", True)
    print("[awq] Applied Hammer-specific AutoAWQ Catcher patch")


def resolve_calibration_seqlen(requested: int, model: Any) -> int:
    requested = max(int(requested), 1)
    config = getattr(model, "config", None)

    max_positions = None
    if config is not None:
        candidates = []
        for attr in ("max_position_embeddings", "max_sequence_length"):
            value = getattr(config, attr, None)
            if isinstance(value, int) and value > 0:
                candidates.append(value)
        if candidates:
            max_positions = min(candidates)

    if max_positions is not None and requested > max_positions:
        print(
            f"[awq] Requested calibration seqlen {requested} exceeds model limit {max_positions}; clamping."
        )
        return max_positions

    return requested


def prepare_tokenizer_for_calibration(tokenizer: Any, seqlen: int) -> None:
    try:
        tokenizer.model_max_length = seqlen
    except Exception:
        pass

    init_kwargs = getattr(tokenizer, "init_kwargs", None)
    if isinstance(init_kwargs, dict):
        init_kwargs["model_max_length"] = seqlen


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantize a model to 4-bit AWQ using AutoAWQ.")
    parser.add_argument("--model", required=True, help="HF repo id or local path of the float model to quantize")
    parser.add_argument("--out", required=True, help="Output directory for the quantized model")
    parser.add_argument("--w-bit", type=int, default=4)
    parser.add_argument("--q-group-size", type=int, default=128)
    parser.add_argument("--zero-point", type=int, default=1)
    parser.add_argument("--version", default="GEMM")
    parser.add_argument("--force", action="store_true", help="Re-quantize even if output looks already quantized")
    parser.add_argument(
        "--calib-dataset",
        default=os.environ.get("AWQ_CALIB_DATASET", "pileval"),
        help="Calibration dataset name supported by AutoAWQ (e.g., pileval, wikitext2)",
    )
    parser.add_argument("--nsamples", type=int, default=int(os.environ.get("AWQ_NSAMPLES", "64")))
    parser.add_argument("--seqlen", type=int, default=int(os.environ.get("AWQ_SEQLEN", "2048")))
    args = parser.parse_args()

    model_path = args.model
    out_dir = args.out

    if (not args.force) and is_awq_dir(out_dir):
        print(f"[awq] Using existing quantized model at {out_dir}")
        return 0

    os.makedirs(out_dir, exist_ok=True)

    # Lazy import to avoid import cost when not used
    try:
        from awq import AutoAWQForCausalLM  # type: ignore
        from transformers import AutoTokenizer  # type: ignore
    except Exception as e:
        print(f"[awq] Failed to import AutoAWQ/transformers: {e}", file=sys.stderr)
        return 1

    quant_config = {
        "zero_point": bool(args.zero_point),
        "q_group_size": int(args.q_group_size),
        "w_bit": int(args.w_bit),
        "version": str(args.version),
    }

    print(f"[awq] Loading float model: {model_path}")
    model = AutoAWQForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        use_cache=False,
    )

    hammer_model = is_hammer_model(model_path)
    if hammer_model:
        apply_hammer_awq_patches()

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)

    target_seqlen = resolve_calibration_seqlen(args.seqlen, model)
    prepare_tokenizer_for_calibration(tokenizer, target_seqlen)

    if hammer_model and target_seqlen != int(args.seqlen):
        print(
            f"[awq] Hammer model calibration seqlen adjusted to {target_seqlen}"
        )

    print(f"[awq] Quantizing with config: {json.dumps(quant_config)}")
    try:
        # Newer AutoAWQ variants
        model.quantize(
            tokenizer,
            quant_config=quant_config,
            calib_dataset=args.calib_dataset,
            nsamples=int(args.nsamples),
            seqlen=target_seqlen,
        )
    except TypeError:
        # Older AutoAWQ API without these kwargs
        print("[awq] AutoAWQ API does not accept calib_dataset/nsamples/seqlen; retrying with defaults")
        model.quantize(
            tokenizer,
            quant_config=quant_config,
        )

    print(f"[awq] Saving quantized model to: {out_dir}")
    model.save_quantized(out_dir)
    tokenizer.save_pretrained(out_dir)

    # Mark directory for quick detection next runs
    marker = os.path.join(out_dir, ".awq_ok")
    try:
        with open(marker, "w", encoding="utf-8") as f:
            f.write("ok")
    except Exception:
        pass

    print(f"[awq] Done: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
