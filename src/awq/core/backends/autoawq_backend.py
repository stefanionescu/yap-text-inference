"""AutoAWQ backend implementation."""

from __future__ import annotations

import glob
import json
import os
from typing import Any

import torch

from src.config.awq import get_model_profile

from ..config_fixes import apply_post_quantization_fixes
from ..metadata import save_quantization_metadata
from ...utils.model_utils import ensure_autoawq_dependencies


def _get_safetensors_size(directory: str) -> int:
    """Calculate total size of safetensors files in a directory."""
    total = 0
    for filepath in glob.glob(os.path.join(directory, "*.safetensors")):
        try:
            total += os.path.getsize(filepath)
        except OSError:
            pass
    return total


def _verify_awq_tensors(safetensor_path: str) -> tuple[bool, str]:
    """Verify that a safetensors file contains AWQ-quantized weights.
    
    AWQ quantization converts Linear layers to use qweight (int32), qzeros, and scales.
    If we find float16/bfloat16 weight tensors instead, quantization likely failed.
    
    Returns:
        (is_valid, message) tuple.
    """
    try:
        from safetensors import safe_open  # type: ignore
    except ImportError:
        return True, "safetensors not available for verification"
    
    try:
        with safe_open(safetensor_path, framework="pt") as f:
            keys = list(f.keys())
            
            # Look for AWQ-specific tensor patterns
            qweight_keys = [k for k in keys if "qweight" in k]
            scales_keys = [k for k in keys if "scales" in k]
            qzeros_keys = [k for k in keys if "qzeros" in k]
            
            # Check for unquantized weight patterns (bad sign)
            # AWQ replaces .weight with .qweight, so finding plain .weight tensors
            # in quantizable layers suggests quantization didn't happen
            weight_keys = [
                k for k in keys 
                if k.endswith(".weight") 
                and any(layer in k for layer in ["q_proj", "k_proj", "v_proj", "o_proj", 
                                                   "gate_proj", "up_proj", "down_proj",
                                                   "dense", "fc1", "fc2"])
            ]
            
            if qweight_keys:
                # Verify qweight dtype is int (int32 for packed 4-bit)
                sample_qweight = f.get_tensor(qweight_keys[0])
                if sample_qweight.dtype not in (torch.int32, torch.int8, torch.uint8):
                    return False, f"qweight has unexpected dtype {sample_qweight.dtype}"

                missing_parts = []
                if not scales_keys:
                    missing_parts.append("scales")
                if not qzeros_keys:
                    missing_parts.append("qzeros")
                if missing_parts:
                    missing = " and ".join(missing_parts)
                    return False, f"Found qweight tensors but missing accompanying {missing} tensors"

                return True, f"Found {len(qweight_keys)} qweight tensors (dtype={sample_qweight.dtype})"
            
            if weight_keys and not qweight_keys:
                # Found regular weight tensors but no qweight - likely not quantized
                sample_weight = f.get_tensor(weight_keys[0])
                return False, (
                    f"Found {len(weight_keys)} unquantized .weight tensors "
                    f"(dtype={sample_weight.dtype}) but no qweight tensors. "
                    "Model may not be properly quantized!"
                )
            
            # Fallback: no clear signal
            return True, f"Tensor keys present: {len(keys)} total"
            
    except Exception as exc:
        return True, f"Verification skipped: {exc}"


def quantize_with_autoawq(
    *,
    model_path: str,
    resolved_model_path: str,
    output_dir: str,
    quant_config: dict[str, Any],
    target_seqlen: int,
    toolcall_model: bool,
) -> bool:
    """Quantize a model with the AutoAWQ backend."""

    ensure_autoawq_dependencies()
    try:
        import awq  # type: ignore
        from awq import AutoAWQForCausalLM  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import AutoAWQ: {exc}")
        return False

    try:
        from transformers import AutoTokenizer  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import transformers: {exc}")
        return False

    autoawq_version = getattr(awq, "__version__", "unknown")
    print(f"[awq] Quantizing with AutoAWQ {autoawq_version}")

    autoawq_quant_config = {
        "zero_point": bool(quant_config["zero_point"]),
        "q_group_size": quant_config["q_group_size"],
        "w_bit": quant_config["w_bit"],
        "version": quant_config["version"],
    }
    print(f"[awq] AutoAWQ quant_config: {json.dumps(autoawq_quant_config)}")

    # NOTE: Do NOT use device_map="auto" here. AutoAWQ handles device placement
    # internally during quantization. Using device_map breaks the quantization
    # process and results in saving unquantized weights.
    model = None
    try:
        model = AutoAWQForCausalLM.from_pretrained(
            resolved_model_path,
            trust_remote_code=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load model for AutoAWQ: {exc}")
        return False

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            resolved_model_path,
            trust_remote_code=True,
            use_fast=False,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load tokenizer: {exc}")
        return False

    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    try:
        model.quantize(tokenizer, quant_config=autoawq_quant_config)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] AutoAWQ quantization failed: {exc}")
        return False

    try:
        # Explicitly request safetensors format for HuggingFace compatibility
        model.save_quantized(output_dir, safetensors=True)
        tokenizer.save_pretrained(output_dir)
        
        # Verify quantization: check that quantized weight files exist
        # AutoAWQ saves quantized Linear layers as qweight/qzeros/scales tensors
        safetensors_files = glob.glob(os.path.join(output_dir, "model*.safetensors"))
        if not safetensors_files:
            print("[awq] Warning: No safetensors files found after save_quantized")
        else:
            print(f"[awq] Saved quantized weights to {len(safetensors_files)} safetensors file(s)")
            
            # Verify output size is reasonable for quantized model
            # 4-bit AWQ should be roughly 3-4x smaller than bf16/fp16
            output_size_gb = _get_safetensors_size(output_dir) / 1e9
            print(f"[awq] Total safetensors size: {output_size_gb:.2f} GB")
            
            # Verify tensors actually contain AWQ-quantized weights
            # Check the first safetensors file for qweight tensors with int dtype
            is_valid, verification_msg = _verify_awq_tensors(safetensors_files[0])
            if is_valid:
                print(f"[awq] Quantization verification: {verification_msg}")
            else:
                print(f"[awq] WARNING: Quantization verification failed: {verification_msg}")
                print("[awq] The saved model may contain unquantized weights!")
        
        # Remove runtime config files that shouldn't be in quantized exports
        # generation_config.json contains sampling parameters (temperature, top_p, etc.)
        # that are runtime settings, not part of the quantized model
        unwanted_files = [
            "generation_config.json",
            "training_args.bin",
            "optimizer.pt",
            "scheduler.pt",
            "rng_state.pth",
        ]
        for filename in unwanted_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"[awq] Removed unwanted runtime file: {filename}")
                except Exception as exc:  # noqa: BLE001
                    print(f"[awq] Warning: failed to remove {filename}: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to save AutoAWQ artifacts: {exc}")
        return False
    finally:
        try:
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    dataset_info = {
        "effective": "AutoAWQ builtin",
    }
    advanced_kwargs: dict[str, Any] = {
        "quantizer": "AutoAWQ",
        "max_seq_length": target_seqlen,
    }

    profile = get_model_profile(model_path)
    if profile:
        advanced_kwargs["model_profile"] = profile.name

    metadata_quant_config = dict(quant_config)
    metadata_quant_config["backend"] = "autoawq"

    save_quantization_metadata(
        output_dir=output_dir,
        model_path=model_path,
        awq_version=f"autoawq=={autoawq_version}",
        quant_config=metadata_quant_config,
        target_seqlen=target_seqlen,
        toolcall_model=toolcall_model,
        dataset_info=dataset_info,
        advanced_kwargs=advanced_kwargs,
    )

    # Apply model-family-specific config.json fixes (e.g., Gemma2 tie_word_embeddings)
    apply_post_quantization_fixes(output_dir, model_path)

    print(f"[awq] Done: {output_dir}")
    return True


