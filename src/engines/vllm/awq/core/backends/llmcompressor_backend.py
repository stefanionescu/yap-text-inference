"""llmcompressor backend implementation."""

from __future__ import annotations

import json
import os
from typing import Any

import torch

# Suppress tokenizers parallelism warnings when forking during calibration
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from src.config.awq import AWQ_DEFAULT_DATASET
from src.helpers.awq import (
    canonicalize_dataset_name,
    dataset_fallback,
    dataset_key,
)
from src.helpers.model_profiles import get_model_profile

from ..calibration import CalibrationConfig
from ..config_fixes import apply_post_quantization_fixes
from ..metadata import save_quantization_metadata


def quantize_with_llmcompressor(
    *,
    calibration_config: CalibrationConfig,
    model_path: str,
    resolved_model_path: str,
    output_dir: str,
    quant_config: dict[str, Any],
    target_seqlen: int,
    hf_model_type: str,
    calibration_kind: str,
) -> bool:
    """Quantize a model with the llmcompressor backend."""

    try:
        import llmcompressor  # type: ignore
        from llmcompressor import oneshot  # type: ignore
        from llmcompressor.modifiers.awq import AWQModifier  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import llmcompressor: {exc}")
        return False

    compressor_version = getattr(llmcompressor, "__version__", "unknown")
    requested_dataset = calibration_config.dataset or AWQ_DEFAULT_DATASET
    dataset = canonicalize_dataset_name(requested_dataset)
    if dataset != dataset_key(requested_dataset):
        print(f"[awq] Dataset alias detected: '{requested_dataset}' -> '{dataset}'")
    dataset_info: dict[str, str] = {
        "requested": requested_dataset,
        "effective": dataset,
    }

    recipe = [
        AWQModifier(
            scheme=quant_config["scheme"],
            targets=quant_config["targets"],
            ignore=quant_config["ignore"],
        )
    ]

    print(f"[awq] Quantizing with llmcompressor {compressor_version}")
    print(f"[awq] Quantization config: {json.dumps(quant_config)}")
    print(
        "[awq] Running oneshot() with dataset="
        f"{dataset_info['effective']}, nsamples={calibration_config.nsamples}, "
        f"max_seq_length={target_seqlen}"
    )

    print(f"[awq] Loading model from {resolved_model_path}")
    try:
        from transformers import AutoModelForCausalLM  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import transformers: {exc}")
        return False

    load_kwargs: dict[str, Any] = {
        "dtype": torch.bfloat16,
        "trust_remote_code": True,
        "device_map": None,
    }

    model = None
    try:
        model = AutoModelForCausalLM.from_pretrained(resolved_model_path, **load_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load model: {exc}")
        return False

    def _run_oneshot(dataset_name: str, loaded_model: Any) -> None:
        oneshot(
            model=loaded_model,
            dataset=dataset_name,
            recipe=recipe,
            output_dir=output_dir,
            max_seq_length=target_seqlen,
            num_calibration_samples=calibration_config.nsamples,
        )

    try:
        _run_oneshot(dataset_info["effective"], model)
    except Exception as exc:  # noqa: BLE001
        fallback_dataset = None
        if _is_dataset_registration_error(exc):
            fallback_dataset = dataset_fallback(dataset_info["effective"])
        if fallback_dataset and fallback_dataset != dataset_info["effective"]:
            print(
                "[awq] Dataset "
                f"'{dataset_info['effective']}' unavailable; retrying with "
                f"'{fallback_dataset}'"
            )
            dataset_info["fallback_from"] = dataset_info["effective"]
            dataset_info["effective"] = fallback_dataset
            try:
                _run_oneshot(fallback_dataset, model)
            except Exception as final_exc:  # noqa: BLE001
                _log_llmcompressor_exception(final_exc, prefix="after fallback")
                return False
        else:
            _log_llmcompressor_exception(exc)
            return False
    finally:
        if model is not None:
            try:
                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    advanced_kwargs: dict[str, Any] = {
        "dataset": dataset_info["effective"],
        "requested_dataset": dataset_info["requested"],
        "num_calibration_samples": calibration_config.nsamples,
        "max_seq_length": target_seqlen,
        "model_type": calibration_kind,
    }
    if hf_model_type:
        advanced_kwargs["hf_model_type"] = hf_model_type
    if "fallback_from" in dataset_info:
        advanced_kwargs["dataset_fallback_from"] = dataset_info["fallback_from"]

    profile = get_model_profile(model_path)
    if profile:
        advanced_kwargs["model_profile"] = profile.name

    metadata_quant_config = dict(quant_config)
    metadata_quant_config["backend"] = "llmcompressor"

    save_quantization_metadata(
        output_dir=output_dir,
        model_path=model_path,
        awq_version=f"llmcompressor=={compressor_version}",
        quant_config=metadata_quant_config,
        target_seqlen=target_seqlen,
        dataset_info=dataset_info,
        advanced_kwargs=advanced_kwargs,
    )

    # Apply model-family-specific config.json fixes (e.g., Gemma2 tie_word_embeddings)
    apply_post_quantization_fixes(output_dir, model_path)

    print(f"[awq] Done: {output_dir}")
    return True


def _log_llmcompressor_exception(exc: Exception, prefix: str | None = None) -> None:
    """Dump llmcompressor failures with the full traceback for easier debugging."""

    import traceback

    scope = f" {prefix}" if prefix else ""
    print(f"[awq] Quantization failed via llmcompressor{scope}: {exc}")
    traceback.print_exception(type(exc), exc, exc.__traceback__)


def _is_dataset_registration_error(exc: Exception) -> bool:
    message = str(exc)
    return "Unable to find" in message and "TextGenerationDataset" in message


