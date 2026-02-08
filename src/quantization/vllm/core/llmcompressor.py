"""llmcompressor backend implementation."""

from __future__ import annotations

import os
import traceback
import contextlib
from typing import Any

import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from src.state import CalibrationConfig, _DatasetInfo
from src.helpers.profiles import get_model_profile
from src.config.calibration import CALIB_DEFAULT_DATASET
from src.helpers.calibration import dataset_key, dataset_fallback, canonicalize_dataset_name

from .fixes import apply_post_quantization_fixes
from .metadata import save_quantization_metadata


def quantize(
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
        import llmcompressor  # noqa: PLC0415
        from llmcompressor import oneshot  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import llmcompressor: {exc}")
        return False

    compressor_version = getattr(llmcompressor, "__version__", "unknown")
    dataset_info = _resolve_dataset(calibration_config)

    recipe = _build_recipe(quant_config)

    try:
        from transformers import AutoModelForCausalLM  # type: ignore[import]  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import transformers: {exc}")
        return False

    load_kwargs: dict[str, Any] = {
        "dtype": torch.bfloat16,
        "trust_remote_code": True,
        "device_map": None,
    }

    try:
        model = AutoModelForCausalLM.from_pretrained(resolved_model_path, **load_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to load model: {exc}")
        return False

    try:
        _run_quantization(
            oneshot=oneshot,
            recipe=recipe,
            dataset_info=dataset_info,
            calibration_config=calibration_config,
            output_dir=output_dir,
            target_seqlen=target_seqlen,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Quantization failed: {exc}")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        return False
    finally:
        _cleanup_model(model)

    _persist_metadata(
        model_path=model_path,
        quant_config=quant_config,
        compressor_version=compressor_version,
        dataset_info=dataset_info,
        target_seqlen=target_seqlen,
        calibration_config=calibration_config,
        hf_model_type=hf_model_type,
        calibration_kind=calibration_kind,
        output_dir=output_dir,
    )

    apply_post_quantization_fixes(output_dir, model_path)
    print("[awq] ✓ llmcompressor quantization done")
    print()
    return True


def _resolve_dataset(config: CalibrationConfig) -> _DatasetInfo:
    requested = config.dataset or CALIB_DEFAULT_DATASET
    canonical = canonicalize_dataset_name(requested)
    if canonical != dataset_key(requested):
        print(f"[awq] Dataset alias detected: '{requested}' -> '{canonical}'")
    return _DatasetInfo(requested=requested, effective=canonical)


def _build_recipe(quant_config: dict[str, Any]) -> list[Any]:
    return [
        _awq_modifier()(  # type: ignore[misc]
            scheme=quant_config["scheme"],
            targets=quant_config["targets"],
            ignore=quant_config["ignore"],
        )
    ]


def _awq_modifier():
    from llmcompressor.modifiers.awq import AWQModifier  # noqa: PLC0415

    return AWQModifier


def _run_quantization(
    *,
    oneshot,
    recipe: list[Any],
    dataset_info: _DatasetInfo,
    calibration_config: CalibrationConfig,
    output_dir: str,
    target_seqlen: int,
    model: Any,
) -> None:
    def _run(dataset_name: str) -> None:
        oneshot(
            model=model,
            dataset=dataset_name,
            recipe=recipe,
            output_dir=output_dir,
            max_seq_length=target_seqlen,
            num_calibration_samples=calibration_config.nsamples,
        )

    try:
        _run(dataset_info.effective)
    except Exception as exc:  # noqa: BLE001
        if _is_dataset_registration_error(exc):
            fallback = dataset_fallback(dataset_info.effective)
            if fallback and fallback != dataset_info.effective:
                dataset_info.fallback_from = dataset_info.effective
                dataset_info.effective = fallback
                print(f"[awq] Dataset '{dataset_info.fallback_from}' unavailable; retrying with '{fallback}'")
                _run(fallback)
                return
        raise


def _cleanup_model(model: Any) -> None:
    if model is None:
        return
    with contextlib.suppress(Exception):
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _persist_metadata(
    *,
    model_path: str,
    quant_config: dict[str, Any],
    compressor_version: str,
    dataset_info: _DatasetInfo,
    target_seqlen: int,
    calibration_config: CalibrationConfig,
    hf_model_type: str,
    calibration_kind: str,
    output_dir: str,
) -> None:
    advanced_kwargs: dict[str, Any] = {
        "dataset": dataset_info.effective,
        "requested_dataset": dataset_info.requested,
        "num_calibration_samples": calibration_config.nsamples,
        "max_seq_length": target_seqlen,
        "model_type": calibration_kind,
    }
    if hf_model_type:
        advanced_kwargs["hf_model_type"] = hf_model_type
    if dataset_info.fallback_from:
        advanced_kwargs["dataset_fallback_from"] = dataset_info.fallback_from

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
        dataset_info={
            "requested": dataset_info.requested,
            "effective": dataset_info.effective,
            **({"fallback_from": dataset_info.fallback_from} if dataset_info.fallback_from else {}),
        },
        advanced_kwargs=advanced_kwargs,
    )


def _is_dataset_registration_error(exc: Exception) -> bool:
    return "Unable to find" in str(exc) and "TextGenerationDataset" in str(exc)


__all__ = ["quantize"]
