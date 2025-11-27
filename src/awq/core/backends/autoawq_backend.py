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


def _collect_awq_tensor_keys(keys: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return qweight/scales/qzeros/weight key groupings for verification."""
    qweight_keys = [k for k in keys if "qweight" in k]
    scales_keys = [k for k in keys if "scales" in k]
    qzeros_keys = [k for k in keys if "qzeros" in k]

    weight_keys = [
        k
        for k in keys
        if k.endswith(".weight")
        and any(
            layer in k
            for layer in [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
                "dense",
                "fc1",
                "fc2",
            ]
        )
    ]
    return qweight_keys, scales_keys, qzeros_keys, weight_keys


def _validate_qweight_tensors(
    tensor_reader: Any,
    qweight_keys: list[str],
    scales_keys: list[str],
    qzeros_keys: list[str],
) -> tuple[bool, str]:
    """Ensure qweight tensors have the expected dtype and companions."""
    sample_qweight = tensor_reader.get_tensor(qweight_keys[0])
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


def _report_unquantized_weights(
    tensor_reader: Any,
    weight_keys: list[str],
) -> tuple[bool, str]:
    """Describe the unquantized weights discovered in verification."""
    sample_weight = tensor_reader.get_tensor(weight_keys[0])
    return False, (
        f"Found {len(weight_keys)} unquantized .weight tensors "
        f"(dtype={sample_weight.dtype}) but no qweight tensors. "
        "Model may not be properly quantized!"
    )


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
        with safe_open(safetensor_path, framework="pt") as tensor_reader:
            keys = list(tensor_reader.keys())
            qweight_keys, scales_keys, qzeros_keys, weight_keys = _collect_awq_tensor_keys(keys)
            
            if qweight_keys:
                return _validate_qweight_tensors(tensor_reader, qweight_keys, scales_keys, qzeros_keys)
            
            if weight_keys:
                return _report_unquantized_weights(tensor_reader, weight_keys)
            
            # Fallback: no clear signal
            return True, f"Tensor keys present: {len(keys)} total"
            
    except Exception as exc:
        return True, f"Verification skipped: {exc}"


def _import_autoawq_stack() -> tuple[Any, Any, Any] | None:
    """Load AutoAWQ/transformers dependencies after ensuring compatibility shims."""
    ensure_autoawq_dependencies()
    try:
        import awq  # type: ignore
        from awq import AutoAWQForCausalLM  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import AutoAWQ: {exc}")
        return None

    try:
        from transformers import AutoTokenizer  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import transformers: {exc}")
        return None

    return awq, AutoAWQForCausalLM, AutoTokenizer


def _build_autoawq_quant_config(quant_config: dict[str, Any]) -> dict[str, Any]:
    """Construct the quantization config passed into AutoAWQ."""
    return {
        "zero_point": bool(quant_config["zero_point"]),
        "q_group_size": quant_config["q_group_size"],
        "w_bit": quant_config["w_bit"],
        "version": quant_config["version"],
    }


def _load_autoawq_model(model_cls: Any, resolved_model_path: str) -> Any | None:
    """Load the base model using AutoAWQ utilities."""
    try:
        return model_cls.from_pretrained(
            resolved_model_path,
            trust_remote_code=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load model for AutoAWQ: {exc}")
        return None


def _load_autoawq_tokenizer(tokenizer_cls: Any, resolved_model_path: str) -> Any | None:
    """Load the tokenizer used for quantization."""
    try:
        return tokenizer_cls.from_pretrained(
            resolved_model_path,
            trust_remote_code=True,
            use_fast=False,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load tokenizer: {exc}")
        return None


def _maybe_set_pad_token(tokenizer: Any) -> None:
    """Backfill pad token if the tokenizer only defines eos_token."""
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token


def _execute_autoawq_quantization(
    model: Any,
    tokenizer: Any,
    autoawq_quant_config: dict[str, Any],
) -> bool:
    """Run the quantization pass with AutoAWQ."""
    try:
        model.quantize(tokenizer, quant_config=autoawq_quant_config)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] AutoAWQ quantization failed: {exc}")
        return False


def _verify_saved_quantization_artifacts(output_dir: str) -> None:
    """Run post-save sanity checks on safetensors outputs."""
    safetensors_files = glob.glob(os.path.join(output_dir, "model*.safetensors"))
    if not safetensors_files:
        print("[awq] Warning: No safetensors files found after save_quantized")
        return

    print(f"[awq] Saved quantized weights to {len(safetensors_files)} safetensors file(s)")
    output_size_gb = _get_safetensors_size(output_dir) / 1e9
    print(f"[awq] Total safetensors size: {output_size_gb:.2f} GB")

    is_valid, verification_msg = _verify_awq_tensors(safetensors_files[0])
    if is_valid:
        print(f"[awq] Quantization verification: {verification_msg}")
    else:
        print(f"[awq] WARNING: Quantization verification failed: {verification_msg}")
        print("[awq] The saved model may contain unquantized weights!")


def _remove_unwanted_runtime_files(output_dir: str) -> None:
    """Drop training/runtime artifacts that should not ship with quantized exports."""
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


def _save_autoawq_outputs(model: Any, tokenizer: Any, output_dir: str) -> bool:
    """Persist quantized artifacts and perform post-save cleanup."""
    try:
        model.save_quantized(output_dir, safetensors=True)
        tokenizer.save_pretrained(output_dir)
        _verify_saved_quantization_artifacts(output_dir)
        _remove_unwanted_runtime_files(output_dir)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to save AutoAWQ artifacts: {exc}")
        return False


def _cleanup_autoawq_model(model: Any) -> None:
    """Release GPU memory by deleting the model reference."""
    try:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _persist_autoawq_metadata(
    *,
    output_dir: str,
    model_path: str,
    autoawq_version: str,
    quant_config: dict[str, Any],
    target_seqlen: int,
    toolcall_model: bool,
) -> None:
    """Write metadata artifacts and apply config patches."""
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

    apply_post_quantization_fixes(output_dir, model_path)
    print(f"[awq] Done: {output_dir}")


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

    autoawq_stack = _import_autoawq_stack()
    if autoawq_stack is None:
        return False
    awq_module, AutoAWQForCausalLM, AutoTokenizer = autoawq_stack

    autoawq_version = getattr(awq_module, "__version__", "unknown")
    print(f"[awq] Quantizing with AutoAWQ {autoawq_version}")

    autoawq_quant_config = _build_autoawq_quant_config(quant_config)
    print(f"[awq] AutoAWQ quant_config: {json.dumps(autoawq_quant_config)}")

    model = _load_autoawq_model(AutoAWQForCausalLM, resolved_model_path)
    if model is None:
        return False

    tokenizer = _load_autoawq_tokenizer(AutoTokenizer, resolved_model_path)
    if tokenizer is None:
        return False

    _maybe_set_pad_token(tokenizer)

    if not _execute_autoawq_quantization(model, tokenizer, autoawq_quant_config):
        return False

    try:
        if not _save_autoawq_outputs(model, tokenizer, output_dir):
            return False
    finally:
        _cleanup_autoawq_model(model)

    _persist_autoawq_metadata(
        output_dir=output_dir,
        model_path=model_path,
        autoawq_version=autoawq_version,
        quant_config=quant_config,
        target_seqlen=target_seqlen,
        toolcall_model=toolcall_model,
    )
    return True


