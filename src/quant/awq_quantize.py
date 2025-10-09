#!/usr/bin/env python3
import argparse
import inspect
import json
import os
import sys
from datetime import datetime
from textwrap import dedent
from typing import Any, Iterable

from awq_chat_adapter import compute_chat_calibration_seqlen
from awq_hammer_adapter import (
    apply_hammer_awq_adapters,
    compute_hammer_calibration_seqlen,
    is_hammer_model,
)


_ADVANCED_QUANTIZE_SUPPORTED: bool | None = None


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
        os.path.join(path, "model.safetensors"),
    ]
    for cand in candidates:
        if file_exists(cand):
            return True
    return False


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
    def _maybe_set_attr(obj: Any, attr: str, value: int) -> None:
        if not hasattr(obj, attr):
            try:
                setattr(obj, attr, value)
            except Exception:
                pass
            return

        try:
            current = getattr(obj, attr)
        except Exception:
            current = None

        try:
            if isinstance(current, int) and current > 0:
                if current < value:
                    setattr(obj, attr, value)
            else:
                setattr(obj, attr, value)
        except Exception:
            pass

    current_len = getattr(tokenizer, "model_max_length", 0)
    if not isinstance(current_len, int):
        current_len = 0
    max_len_target = max(seqlen, current_len, 1_000_000)
    _maybe_set_attr(tokenizer, "model_max_length", max_len_target)

    init_kwargs = getattr(tokenizer, "init_kwargs", None)
    if isinstance(init_kwargs, dict):
        for key in ("model_max_length", "max_length", "max_position_embeddings"):
            current = init_kwargs.get(key)
            if not isinstance(current, int) or current <= 0 or current < max_len_target:
                init_kwargs[key] = max_len_target

    for attr in (
        "max_len_single_sentence",
        "max_len_sentences_pair",
        "max_length",
        "n_positions",
    ):
        _maybe_set_attr(tokenizer, attr, max_len_target)


def _quantize_supports_kwargs(quantize_fn: Any, keys: Iterable[str]) -> bool:
    try:
        sig = inspect.signature(quantize_fn)
    except (TypeError, ValueError):
        return True

    params = sig.parameters
    for param in params.values():
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            return True

    return all(key in params for key in keys)


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

    try:
        import awq as awq_pkg  # type: ignore
        from awq import AutoAWQForCausalLM  # type: ignore
        from transformers import AutoTokenizer  # type: ignore
    except Exception as e:
        print(f"[awq] Failed to import AutoAWQ/transformers: {e}", file=sys.stderr)
        return 1
    awq_version = getattr(awq_pkg, "__version__", "unknown")

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

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)

    requested_seqlen = int(args.seqlen)
    if hammer_model:
        requested_seqlen = compute_hammer_calibration_seqlen(requested_seqlen)
    else:
        requested_seqlen = compute_chat_calibration_seqlen(requested_seqlen)

    target_seqlen = resolve_calibration_seqlen(requested_seqlen, model)
    prepare_tokenizer_for_calibration(tokenizer, target_seqlen)

    if hammer_model:
        apply_hammer_awq_adapters(target_seqlen)
        if target_seqlen != requested_seqlen:
            print(f"[awq] Hammer model calibration seqlen adjusted to {target_seqlen}")
    else:
        if target_seqlen != requested_seqlen:
            print(f"[awq] Chat model calibration seqlen adjusted to {target_seqlen}")

    print(f"[awq] Quantizing with config: {json.dumps(quant_config)}")

    quant_kwargs = {
        "tokenizer": tokenizer,
        "quant_config": quant_config,
    }
    advanced_kwargs = {
        "calib_dataset": args.calib_dataset,
        "nsamples": int(args.nsamples),
        "seqlen": target_seqlen,
    }

    global _ADVANCED_QUANTIZE_SUPPORTED
    if _ADVANCED_QUANTIZE_SUPPORTED is None:
        supports_advanced = _quantize_supports_kwargs(model.quantize, advanced_kwargs.keys())
    else:
        supports_advanced = _ADVANCED_QUANTIZE_SUPPORTED
    if supports_advanced:
        quant_kwargs.update(advanced_kwargs)

    try:
        model.quantize(**quant_kwargs)
    except TypeError:
        if supports_advanced:
            _ADVANCED_QUANTIZE_SUPPORTED = False
            supports_advanced = False
            model.quantize(tokenizer=tokenizer, quant_config=quant_config)
        else:
            raise
    else:
        if _ADVANCED_QUANTIZE_SUPPORTED is None:
            _ADVANCED_QUANTIZE_SUPPORTED = supports_advanced

    print(f"[awq] Saving quantized model to: {out_dir}")
    model.save_quantized(out_dir)
    tokenizer.save_pretrained(out_dir)

    calibration_mode = "explicit" if supports_advanced else "auto"
    metadata = {
        "source_model": model_path,
        "awq_version": awq_version,
        "quant_config": quant_config,
        "hammer_model": hammer_model,
        "calibration": {
            "mode": calibration_mode,
            "dataset": args.calib_dataset if supports_advanced else "auto",
            "nsamples": int(args.nsamples) if supports_advanced else None,
            "seqlen": target_seqlen,
        },
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    meta_path = os.path.join(out_dir, "awq_metadata.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
    except Exception as exc:
        print(f"[awq] Warning: failed to write metadata ({exc})")

    quant_summary = json.dumps(quant_config, indent=2)
    if supports_advanced:
        calib_section = dedent(
            f"""
            - Calibration dataset: `{args.calib_dataset}`
            - Calibration samples: {int(args.nsamples)}
            - Calibration sequence length: {target_seqlen}
            """
        )
    else:
        calib_section = "- Calibration: AutoAWQ default pipeline"

    readme_contents = dedent(
        f"""
        # AWQ Quantized Model

        - Source model: `{model_path}`
        - AWQ version: `{awq_version}`
        - Quantization config:
        ```json
        {quant_summary}
        ```
        - Generated: {metadata['generated_at']}

        ## Calibration

        {calib_section}

        ## Usage

        The contents of this repository were produced by the Yap Text Inference
        pipeline using AutoAWQ. You can load the weights with libraries such as
        `vllm` or `auto-gptq` that support AWQ checkpoints. Example with vLLM:

        ```python
        from vllm import LLM

        engine = LLM(
            model="{os.path.basename(out_dir)}",
            quantization="awq",
            trust_remote_code=True,
        )
        ```

        Ensure your runtime uses the same or newer CUDA/Torch stack as the
        environment that produced this model to avoid kernel incompatibilities.
        """
    ).strip() + "\n"

    readme_path = os.path.join(out_dir, "README.md")
    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_contents)
    except Exception as exc:
        print(f"[awq] Warning: failed to write README ({exc})")

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
