"""Core AWQ quantization logic powered by llmcompressor."""

import json
import os
import time
from typing import Any

from ..adapters import (
    apply_awq_compatibility_patches,
    compute_chat_calibration_seqlen,
    compute_toolcall_calibration_seqlen,
    is_toolcall_model,
)
from ..utils import resolve_calibration_seqlen, generate_readme, is_awq_dir
from .calibration import CalibrationConfig

_DEFAULT_DATASET = "open_platypus"
_DATASET_ALIASES = {
    "open-platypus": "open_platypus",
    "openplatypus": "open_platypus",
    "wikitext2": "wikitext",
    "wiki_text": "wikitext",
}
_DATASET_FALLBACKS = {
    "pileval": _DEFAULT_DATASET,
    "pile_val": _DEFAULT_DATASET,
    "pile": _DEFAULT_DATASET,
}


def _dataset_key(name: str | None) -> str:
    raw = (name or "").strip()
    if not raw:
        return _DEFAULT_DATASET
    return raw.lower().replace("-", "_").replace(" ", "_")


def _canonicalize_dataset_name(name: str | None) -> str:
    key = _dataset_key(name)
    return _DATASET_ALIASES.get(key, key or _DEFAULT_DATASET)


def _dataset_fallback(name: str) -> str | None:
    return _DATASET_FALLBACKS.get(_dataset_key(name))


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
        """Quantize a model using llmcompressor's AWQ pipeline."""
        
        if not force and is_awq_dir(output_dir):
            print(f"[awq] Using existing quantized model at {output_dir}")
            return True
            
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            import llmcompressor  # type: ignore
            from llmcompressor import oneshot  # type: ignore
            from llmcompressor.modifiers.awq import AWQModifier  # type: ignore
        except Exception as exc:  # noqa: BLE001
            print(f"[awq] Failed to import llmcompressor: {exc}")
            return False
            
        apply_awq_compatibility_patches()
        compressor_version = getattr(llmcompressor, "__version__", "unknown")
        
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
        toolcall_model = is_toolcall_model(model_path)

        if toolcall_model:
            requested_seqlen = compute_toolcall_calibration_seqlen(self.config.seqlen)
        else:
            requested_seqlen = compute_chat_calibration_seqlen(self.config.seqlen)

        target_seqlen = resolve_calibration_seqlen(requested_seqlen, model_config)
        model_type = "Toolcall" if toolcall_model else "Chat"
        if target_seqlen != requested_seqlen:
            print(f"[awq] {model_type} model calibration seqlen adjusted to {target_seqlen}")
        else:
            print(f"[awq] {model_type} model calibration seqlen = {target_seqlen}")

        recipe = [
            AWQModifier(
                scheme=quant_config["scheme"],
                targets=quant_config["targets"],
                ignore=quant_config["ignore"],
            )
        ]

        requested_dataset = self.config.dataset or _DEFAULT_DATASET
        dataset = _canonicalize_dataset_name(requested_dataset)
        if dataset != _dataset_key(requested_dataset):
            print(f"[awq] Dataset alias detected: '{requested_dataset}' -> '{dataset}'")
        dataset_info: dict[str, str] = {
            "requested": requested_dataset,
            "effective": dataset,
        }

        print(f"[awq] Quantizing with llmcompressor {compressor_version}")
        print(f"[awq] Quantization config: {json.dumps(quant_config)}")
        print(
            "[awq] Running oneshot() with dataset="
            f"{dataset_info['effective']}, nsamples={self.config.nsamples}, "
            f"max_seq_length={target_seqlen}"
        )

        def _run_oneshot(dataset_name: str) -> None:
            oneshot(
                model=resolved_model_path,
                dataset=dataset_name,
                recipe=recipe,
                output_dir=output_dir,
                max_seq_length=target_seqlen,
                num_calibration_samples=self.config.nsamples,
            )

        try:
            _run_oneshot(dataset_info["effective"])
        except Exception as exc:  # noqa: BLE001
            fallback_dataset = None
            if _is_dataset_registration_error(exc):
                fallback_dataset = _dataset_fallback(dataset_info["effective"])
            if fallback_dataset and fallback_dataset != dataset_info["effective"]:
                print(
                    "[awq] Dataset "
                    f"'{dataset_info['effective']}' unavailable; retrying with "
                    f"'{fallback_dataset}'"
                )
                dataset_info["fallback_from"] = dataset_info["effective"]
                dataset_info["effective"] = fallback_dataset
                try:
                    _run_oneshot(fallback_dataset)
                except Exception as final_exc:  # noqa: BLE001
                    print(f"[awq] Quantization failed via llmcompressor after fallback: {final_exc}")
                    return False
            else:
                print(f"[awq] Quantization failed via llmcompressor: {exc}")
                return False

        advanced_kwargs = {
            "dataset": dataset_info["effective"],
            "requested_dataset": dataset_info["requested"],
            "num_calibration_samples": self.config.nsamples,
            "max_seq_length": target_seqlen,
            "model_type": model_type,
        }
        if "fallback_from" in dataset_info:
            advanced_kwargs["dataset_fallback_from"] = dataset_info["fallback_from"]

        self._save_metadata(
            output_dir=output_dir,
            model_path=model_path,
            awq_version=f"llmcompressor=={compressor_version}",
            quant_config=quant_config,
            target_seqlen=target_seqlen,
            toolcall_model=toolcall_model,
            dataset_info=dataset_info,
            advanced_kwargs=advanced_kwargs,
        )

        print(f"[awq] Done: {output_dir}")
        return True

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
            
        if advanced_kwargs:
            dataset_desc = advanced_kwargs.get("dataset", "Unknown")
            fallback_from = advanced_kwargs.get("dataset_fallback_from")
            if fallback_from:
                dataset_desc = f"{dataset_desc} (fallback from {fallback_from})"
            calib_section = f"""### Calibration
            
- **Dataset**: {dataset_desc}
- **Samples**: {advanced_kwargs.get('num_calibration_samples', 'Unknown')}
- **Sequence Length**: {advanced_kwargs.get('max_seq_length', 'Unknown')}
- **Model Type**: {'Toolcall (Tool)' if toolcall_model else 'Chat'}
- **Compressor**: {awq_version}
"""
        else:
            calib_section = "- Calibration: llmcompressor default pipeline"
            
        quant_summary = json.dumps(quant_config, indent=2)
        readme_contents = generate_readme(
            model_path=model_path,
            awq_version=awq_version,
            quant_summary=quant_summary,
            metadata=metadata,
            calib_section=calib_section,
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
