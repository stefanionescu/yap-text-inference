"""AutoAWQ backend implementation."""

from __future__ import annotations

import glob
import json
import os
from typing import Any

import torch

from src.config.awq import get_model_profile

from ..metadata import save_quantization_metadata
from ...utils.model_utils import ensure_autoawq_dependencies


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
        # Note: save_quantized should ONLY save quantized weights (qweight/qzeros/scales)
        # and non-quantized layers (embeddings, layer_norms) in their original precision
        model.save_quantized(output_dir, safetensors=True)
        tokenizer.save_pretrained(output_dir)
        
        # Verify quantization: check that quantized weight files exist
        # AutoAWQ saves quantized Linear layers as qweight/qzeros/scales tensors
        safetensors_files = glob.glob(os.path.join(output_dir, "model*.safetensors"))
        if not safetensors_files:
            print("[awq] Warning: No safetensors files found after save_quantized")
        else:
            print(f"[awq] Saved quantized weights to {len(safetensors_files)} safetensors file(s)")
            
            # Verify quantization actually happened by checking safetensors contents
            # AutoAWQ sometimes saves BOTH quantized (qweight) AND unquantized (weight) tensors
            # We need to ensure only quantized tensors exist for Linear layers
            try:
                from safetensors import safe_open
                unquantized_linear_weights = []
                quantized_layers = []
                
                for safetensor_file in safetensors_files:
                    with safe_open(safetensor_file, framework="pt") as f:
                        keys = f.keys()
                        for key in keys:
                            # Check for unquantized Linear layer weights (should NOT exist)
                            if ".weight" in key and any(x in key for x in ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]):
                                if "qweight" not in key and "qzeros" not in key and "scales" not in key:
                                    unquantized_linear_weights.append(key)
                            # Track quantized layers
                            if "qweight" in key:
                                layer_name = key.split(".qweight")[0]
                                if layer_name not in quantized_layers:
                                    quantized_layers.append(layer_name)
                
                if unquantized_linear_weights:
                    print(f"[awq] ERROR: Found {len(unquantized_linear_weights)} unquantized Linear weight tensors!")
                    print(f"[awq] These should not exist in quantized model: {unquantized_linear_weights[:5]}...")
                    print("[awq] This indicates quantization may have failed or saved duplicate weights")
                    return False
                
                if quantized_layers:
                    print(f"[awq] Verified quantization: {len(quantized_layers)} Linear layers quantized")
                else:
                    print("[awq] WARNING: No quantized layers found! Quantization may have failed")
                    return False
                
                # Check total file size - quantized models should be significantly smaller
                total_size = sum(os.path.getsize(f) for f in safetensors_files)
                total_size_gb = total_size / (1024**3)
                print(f"[awq] Total safetensors size: {total_size_gb:.2f} GB")
                
                # Calculate size breakdown
                try:
                    embedding_size = 0
                    quantized_size = 0
                    other_size = 0
                    
                    for safetensor_file in safetensors_files:
                        with safe_open(safetensor_file, framework="pt") as f:
                            for key in f.keys():
                                tensor = f.get_tensor_info(key)
                                if tensor_info:
                                    size_bytes = tensor_info.get("data_offsets", [0, 0])[1] - tensor_info.get("data_offsets", [0, 0])[0]
                                    if "embed_tokens" in key:
                                        embedding_size += size_bytes
                                    elif any(x in key for x in ["qweight", "qzeros", "scales"]):
                                        quantized_size += size_bytes
                                    else:
                                        other_size += size_bytes
                    
                    print(f"[awq] Size breakdown: embeddings={embedding_size/(1024**3):.2f}GB, quantized={quantized_size/(1024**3):.2f}GB, other={other_size/(1024**3):.2f}GB")
                except Exception:  # noqa: BLE001
                    pass
                    
            except ImportError:
                print("[awq] Warning: safetensors not available for verification, skipping tensor check")
            except Exception as verify_exc:  # noqa: BLE001
                print(f"[awq] Warning: Failed to verify quantization: {verify_exc}")
        
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

    print(f"[awq] Done: {output_dir}")
    return True


