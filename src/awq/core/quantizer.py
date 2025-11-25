"""Core AWQ quantization logic (llmcompressor + AutoAWQ fallback)."""

import json
import os
import time
import traceback
from typing import Any

import torch

from ..adapters import (
    apply_awq_compatibility_patches,
    compute_chat_calibration_seqlen,
    compute_toolcall_calibration_seqlen,
    is_toolcall_model,
)
from ..utils import resolve_calibration_seqlen, generate_readme, is_awq_dir
from .calibration import CalibrationConfig
from src.config.awq import (
    AWQ_DEFAULT_DATASET,
    canonicalize_dataset_name,
    dataset_fallback,
    dataset_key,
    get_model_profile,
    normalize_model_id,
)


def _is_dataset_registration_error(exc: Exception) -> bool:
    message = str(exc)
    return "Unable to find" in message and "TextGenerationDataset" in message


class AWQQuantizer:
    """AWQ quantization manager backed by llmcompressor."""
    
    def __init__(self, config: CalibrationConfig):
        self.config = config
        
    def quantize_model(
        self,
        model_path: str,
        output_dir: str,
        force: bool = False,
    ) -> bool:
        """Quantize a model using llmcompressor or AutoAWQ (for Qwen)."""

        if not force and is_awq_dir(output_dir):
            print(f"[awq] Using existing quantized model at {output_dir}")
            return True

        os.makedirs(output_dir, exist_ok=True)
        apply_awq_compatibility_patches()

        quant_config = {
            "scheme": f"W{self.config.w_bit}A16",
            "zero_point": self.config.zero_point,
            "q_group_size": self.config.q_group_size,
            "w_bit": self.config.w_bit,
            "version": self.config.version,
            "targets": "Linear",
            "ignore": ["lm_head"],
        }

        resolved_model_path = self._prefetch_model(model_path)
        if resolved_model_path is None:
            return False

        model_config = self._load_model_config(resolved_model_path)
        hf_model_type = getattr(model_config, "model_type", "") if model_config is not None else ""
        requires_autoawq = self._requires_autoawq_backend(model_config, model_path)

        toolcall_model = is_toolcall_model(model_path)
        requested_seqlen = (
            compute_toolcall_calibration_seqlen(self.config.seqlen)
            if toolcall_model
            else compute_chat_calibration_seqlen(self.config.seqlen)
        )
        target_seqlen = resolve_calibration_seqlen(requested_seqlen, model_config)
        calibration_kind = "Toolcall" if toolcall_model else "Chat"
        if target_seqlen != requested_seqlen:
            print(f"[awq] {calibration_kind} model calibration seqlen adjusted to {target_seqlen}")
        else:
            print(f"[awq] {calibration_kind} model calibration seqlen = {target_seqlen}")

        if requires_autoawq:
            return self._quantize_with_autoawq(
                model_path=model_path,
                resolved_model_path=resolved_model_path,
                output_dir=output_dir,
                quant_config=quant_config,
                target_seqlen=target_seqlen,
                toolcall_model=toolcall_model,
            )

        return self._quantize_with_llmcompressor(
            model_path=model_path,
            resolved_model_path=resolved_model_path,
            output_dir=output_dir,
            quant_config=quant_config,
            target_seqlen=target_seqlen,
            toolcall_model=toolcall_model,
            hf_model_type=hf_model_type,
            calibration_kind=calibration_kind,
        )

    def _quantize_with_autoawq(
        self,
        *,
        model_path: str,
        resolved_model_path: str,
        output_dir: str,
        quant_config: dict[str, Any],
        target_seqlen: int,
        toolcall_model: bool,
    ) -> bool:
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

        device_map = "auto" if torch.cuda.is_available() else None
        model = None
        try:
            model = AutoAWQForCausalLM.from_pretrained(
                resolved_model_path,
                trust_remote_code=True,
                device_map=device_map,
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
            model.save_quantized(output_dir)
            tokenizer.save_pretrained(output_dir)
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
            "requested": "AutoAWQ builtin",
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

        self._save_metadata(
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

    def _quantize_with_llmcompressor(
        self,
        *,
        model_path: str,
        resolved_model_path: str,
        output_dir: str,
        quant_config: dict[str, Any],
        target_seqlen: int,
        toolcall_model: bool,
        hf_model_type: str,
        calibration_kind: str,
    ) -> bool:
        try:
            import llmcompressor  # type: ignore
            from llmcompressor import oneshot  # type: ignore
            from llmcompressor.modifiers.awq import AWQModifier  # type: ignore
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Failed to import llmcompressor: {exc}")
            return False

        compressor_version = getattr(llmcompressor, "__version__", "unknown")
        requested_dataset = self.config.dataset or AWQ_DEFAULT_DATASET
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
            f"{dataset_info['effective']}, nsamples={self.config.nsamples}, "
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
                num_calibration_samples=self.config.nsamples,
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
                    self._log_llmcompressor_exception(final_exc, prefix="after fallback")
                    return False
            else:
                self._log_llmcompressor_exception(exc)
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
            "num_calibration_samples": self.config.nsamples,
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

        self._save_metadata(
            output_dir=output_dir,
            model_path=model_path,
            awq_version=f"llmcompressor=={compressor_version}",
            quant_config=metadata_quant_config,
            target_seqlen=target_seqlen,
            toolcall_model=toolcall_model,
            dataset_info=dataset_info,
            advanced_kwargs=advanced_kwargs,
        )

        print(f"[awq] Done: {output_dir}")
        return True

    @staticmethod
    def _log_llmcompressor_exception(exc: Exception, prefix: str | None = None) -> None:
        """Dump llmcompressor failures with the full traceback for easier debugging."""

        scope = f" {prefix}" if prefix else ""
        print(f"[awq] Quantization failed via llmcompressor{scope}: {exc}")
        traceback.print_exception(type(exc), exc, exc.__traceback__)

    def _requires_autoawq_backend(self, model_config: Any | None, model_identifier: str) -> bool:
        """Return True when this model must be quantized with AutoAWQ."""

        model_type = (getattr(model_config, "model_type", "") or "").lower()
        if model_type.startswith("qwen"):
            return True
        if model_type == "mistral3":
            return True

        if not model_type:
            normalized = normalize_model_id(model_identifier)
            qwen_markers = ("qwen3", "qwen2", "qwen")
            mistral3_markers = ("mistral-3", "mistral3", "ms-3", "ms3")
            if any(marker in normalized for marker in qwen_markers):
                return True
            if any(marker in normalized for marker in mistral3_markers):
                return True

        return False

    def _prefetch_model(self, model_path: str) -> str | None:
        """Resolve remote HF repos to a local snapshot for robustness."""

        resolved_model_path = model_path
        if os.path.isdir(model_path) or "/" not in model_path:
            return resolved_model_path

        try:
            from huggingface_hub import snapshot_download  # lazy import
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Failed to import huggingface_hub for snapshot download: {exc}")
            return None

        token = os.environ.get("HUGGINGFACE_HUB_TOKEN") or os.environ.get("HF_TOKEN")
        cache_dir = os.environ.get("HF_HOME")

        print(f"[awq] Prefetching model from Hub: {model_path}")
        last_err: Exception | None = None
        for attempt in range(1, 4):
            try:
                resolved_model_path = snapshot_download(
                    repo_id=model_path,
                    token=token,
                    local_files_only=False,
                    resume_download=True,
                    cache_dir=cache_dir,
                )
                last_err = None
                break
            except Exception as dl_err:  # noqa: BLE001
                last_err = dl_err
                backoff = min(2 ** attempt, 5)
                print(f"[awq] Hub download failed (attempt {attempt}/3): {dl_err}")
                if attempt < 3:
                    print(f"[awq] Retrying in {backoff}s…")
                    time.sleep(backoff)

        if last_err is not None:
            print(
                "[awq] Quantization failed: could not download model from Hugging Face. "
                "Check network access, repository visibility, and set HF_TOKEN or "
                "HUGGINGFACE_HUB_TOKEN if needed."
            )
            return None

        return resolved_model_path

    def _load_model_config(self, model_path: str) -> Any | None:
        """Best-effort load of model config for seqlen validation."""

        try:
            from transformers import AutoConfig  # type: ignore
        except Exception:
            return None

        try:
            return AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Warning: unable to load config for {model_path}: {exc}")
            return None
        
    def _save_metadata(
        self,
        output_dir: str,
        model_path: str,
        awq_version: str,
        quant_config: dict,
        target_seqlen: int,
        toolcall_model: bool,
        dataset_info: dict[str, str] | None = None,
        advanced_kwargs: dict | None = None,
    ) -> None:
        """Save metadata and generate README."""
        
        metadata = {
            "source_model": model_path,
            "awq_version": awq_version,
            "quantization_config": quant_config,
            "calibration_seqlen": target_seqlen,
            "is_toolcall_model": toolcall_model,
            "pipeline": "yap-text-inference",
        }
        
        if dataset_info:
            metadata["calibration_dataset"] = dataset_info

        if advanced_kwargs:
            metadata["calibration_config"] = advanced_kwargs
            
        meta_path = os.path.join(output_dir, "awq_metadata.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Warning: failed to write metadata ({exc})")
            
        quant_summary = json.dumps(quant_config, indent=2)
        readme_contents = generate_readme(
            model_path=model_path,
            awq_version=awq_version,
            quant_summary=quant_summary,
            metadata=metadata,
            out_dir=output_dir,
        )
        
        readme_path = os.path.join(output_dir, "README.md")
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_contents)
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Warning: failed to write README ({exc})")
            
        marker = os.path.join(output_dir, ".awq_ok")
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write("ok")
        except Exception:
            pass
