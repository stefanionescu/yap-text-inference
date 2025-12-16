#!/usr/bin/env python3
"""
Clean AWQ quantization script using the new modular structure.

Usage:
    python -m quant.quantize --model MODEL_PATH --out OUTPUT_DIR [options]
"""

import argparse
import os
import sys

from src.engines.vllm.awq.core import AWQQuantizer, CalibrationConfig
from src.config.models import is_classifier_model


def main() -> int:
    """Main quantization entry point."""
    parser = argparse.ArgumentParser(description="Quantize a model to 4-bit AWQ using llmcompressor.")
    parser.add_argument("--model", required=True, help="HF repo id or local path of the float model to quantize")
    parser.add_argument("--out", required=True, help="Output directory for the quantized model")
    parser.add_argument("--w-bit", type=int, default=4, help="Weight bit precision (default: 4)")
    parser.add_argument("--q-group-size", type=int, default=128, help="Quantization group size (default: 128)")
    parser.add_argument("--zero-point", type=int, default=1, help="Use zero point quantization (default: 1)")
    parser.add_argument("--version", default="GEMM", help="AWQ version (default: GEMM)")
    parser.add_argument("--force", action="store_true", help="Re-quantize even if output looks already quantized")
    parser.add_argument(
        "--calib-dataset",
        default=os.environ.get("AWQ_CALIB_DATASET", "open_platypus"),
        help="Calibration dataset handled by llmcompressor (e.g., open_platypus, wikitext)",
    )
    parser.add_argument("--nsamples", type=int, default=int(os.environ.get("AWQ_NSAMPLES", "64")),
                       help="Number of calibration samples (default: 64)")
    parser.add_argument("--seqlen", type=int, default=int(os.environ.get("AWQ_SEQLEN", "2048")),
                       help="Calibration sequence length (default: 2048)")
    
    args = parser.parse_args()
    
    # Block classifier models from quantization
    if is_classifier_model(args.model):
        print(f"[awq] ERROR: Cannot quantize classifier model '{args.model}'")
        print("[awq] Classifier models use transformers AutoModelForSequenceClassification,")
        print("[awq] not autoregressive LLMs. They don't support AWQ quantization.")
        return 1
    
    # Create calibration config
    config = CalibrationConfig(
        dataset=args.calib_dataset,
        nsamples=args.nsamples,
        seqlen=args.seqlen,
        w_bit=args.w_bit,
        q_group_size=args.q_group_size,
        zero_point=bool(args.zero_point),
        version=args.version,
    )
    
    # Create quantizer and run
    quantizer = AWQQuantizer(config)
    
    try:
        success = quantizer.quantize_model(
            model_path=args.model,
            output_dir=args.out,
            force=args.force
        )
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n[awq] Quantization interrupted by user")
        return 130
    except Exception as e:
        print(f"[awq] Quantization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
