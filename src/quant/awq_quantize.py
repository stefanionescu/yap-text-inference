#!/usr/bin/env python3
import argparse
import json
import os
import sys


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantize a model to 4-bit AWQ using AutoAWQ.")
    parser.add_argument("--model", required=True, help="HF repo id or local path of the float model to quantize")
    parser.add_argument("--out", required=True, help="Output directory for the quantized model")
    parser.add_argument("--w-bit", type=int, default=4)
    parser.add_argument("--q-group-size", type=int, default=128)
    parser.add_argument("--zero-point", type=int, default=1)
    parser.add_argument("--version", default="GEMM")
    parser.add_argument("--force", action="store_true", help="Re-quantize even if output looks already quantized")
    parser.add_argument("--calib-dataset", default=os.environ.get("AWQ_CALIB_DATASET", "pileval"), help="Calibration dataset name supported by AutoAWQ (e.g., pileval, wikitext2)")
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
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)

    print(f"[awq] Quantizing with config: {json.dumps(quant_config)}")
    model.quantize(
        tokenizer,
        quant_config=quant_config,
        calib_dataset=args.calib_dataset,
        nsamples=int(args.nsamples),
        seqlen=int(args.seqlen),
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


