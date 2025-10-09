"""Core AWQ quantization logic."""

import inspect
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from ..adapters import (
    apply_hammer_awq_adapters,
    compute_chat_calibration_seqlen,
    compute_hammer_calibration_seqlen,
    is_hammer_model,
)
from ..utils import resolve_calibration_seqlen, generate_readme, is_awq_dir
from .calibration import CalibrationConfig, prepare_tokenizer_for_calibration


# Global flag for advanced quantization support detection
_ADVANCED_QUANTIZE_SUPPORTED: Optional[bool] = None


def _quantize_supports_kwargs(quantize_fn: Any, keys: Iterable[str]) -> bool:
    """Check if the quantize function supports the given keyword arguments."""
    global _ADVANCED_QUANTIZE_SUPPORTED
    if _ADVANCED_QUANTIZE_SUPPORTED is not None:
        return _ADVANCED_QUANTIZE_SUPPORTED

    try:
        sig = inspect.signature(quantize_fn)
        for param_name, param in sig.parameters.items():
            if param.kind == param.VAR_KEYWORD:  # **kwargs
                _ADVANCED_QUANTIZE_SUPPORTED = True
                return True

        _ADVANCED_QUANTIZE_SUPPORTED = all(key in sig.parameters for key in keys)
        return _ADVANCED_QUANTIZE_SUPPORTED
    except Exception:
        _ADVANCED_QUANTIZE_SUPPORTED = False
        return False


class AWQQuantizer:
    """AWQ quantization manager."""
    
    def __init__(self, config: CalibrationConfig):
        self.config = config
        
    def quantize_model(
        self, 
        model_path: str, 
        output_dir: str,
        force: bool = False
    ) -> bool:
        """Quantize a model using AWQ."""
        
        # Check if already quantized
        if not force and is_awq_dir(output_dir):
            print(f"[awq] Using existing quantized model at {output_dir}")
            return True
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Import dependencies
        try:
            import awq as awq_pkg  # type: ignore
            from awq import AutoAWQForCausalLM  # type: ignore
            from transformers import AutoTokenizer  # type: ignore
        except Exception as e:
            print(f"[awq] Failed to import AutoAWQ/transformers: {e}")
            return False
            
        awq_version = getattr(awq_pkg, "__version__", "unknown")
        
        # Build quantization config
        quant_config = {
            "zero_point": self.config.zero_point,
            "q_group_size": self.config.q_group_size,
            "w_bit": self.config.w_bit,
            "version": self.config.version,
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
        
        # Compute calibration sequence length
        if hammer_model:
            requested_seqlen = compute_hammer_calibration_seqlen(self.config.seqlen)
            apply_hammer_awq_adapters(resolve_calibration_seqlen(requested_seqlen, model))
        else:
            requested_seqlen = compute_chat_calibration_seqlen(self.config.seqlen)
            
        target_seqlen = resolve_calibration_seqlen(requested_seqlen, model)
        prepare_tokenizer_for_calibration(tokenizer, target_seqlen)
        
        if target_seqlen != requested_seqlen:
            model_type = "Hammer" if hammer_model else "Chat"
            print(f"[awq] {model_type} model calibration seqlen adjusted to {target_seqlen}")
            
        print(f"[awq] Quantizing with config: {json.dumps(quant_config)}")
        
        # Prepare quantization arguments
        quant_kwargs = {
            "tokenizer": tokenizer,
            "quant_config": quant_config,
        }
        
        advanced_kwargs = {
            "calib_dataset": self.config.dataset,
            "nsamples": self.config.nsamples,
            "seqlen": target_seqlen,
        }
        
        # Check if advanced quantization is supported
        if _quantize_supports_kwargs(model.quantize, advanced_kwargs.keys()):
            quant_kwargs.update(advanced_kwargs)
            
        try:
            model.quantize(**quant_kwargs)
        except Exception as e:
            print(f"[awq] Quantization failed: {e}")
            return False
            
        # Save the quantized model
        print(f"[awq] Saving quantized model to: {output_dir}")
        model.save_quantized(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        # Generate metadata and README
        self._save_metadata(
            output_dir=output_dir,
            model_path=model_path,
            awq_version=awq_version,
            quant_config=quant_config,
            target_seqlen=target_seqlen,
            hammer_model=hammer_model,
            advanced_kwargs=advanced_kwargs if _quantize_supports_kwargs(model.quantize, advanced_kwargs.keys()) else None
        )
        
        print(f"[awq] Done: {output_dir}")
        return True
        
    def _save_metadata(
        self,
        output_dir: str,
        model_path: str,
        awq_version: str,
        quant_config: Dict,
        target_seqlen: int,
        hammer_model: bool,
        advanced_kwargs: Optional[Dict] = None
    ) -> None:
        """Save metadata and generate README."""
        
        # Save metadata
        metadata = {
            "source_model": model_path,
            "awq_version": awq_version,
            "quantization_config": quant_config,
            "calibration_seqlen": target_seqlen,
            "is_hammer_model": hammer_model,
            "generated_at": datetime.now().isoformat(),
            "pipeline": "yap-text-inference",
        }
        
        if advanced_kwargs:
            metadata["calibration_config"] = advanced_kwargs
            
        # Save metadata file
        meta_path = os.path.join(output_dir, "awq_metadata.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"[awq] Warning: failed to write metadata ({exc})")
            
        # Generate calibration section for README
        if advanced_kwargs:
            calib_section = f"""### Advanced Calibration
            
- **Dataset**: {advanced_kwargs.get('calib_dataset', 'Unknown')}
- **Samples**: {advanced_kwargs.get('nsamples', 'Unknown')}  
- **Sequence Length**: {advanced_kwargs.get('seqlen', 'Unknown')}
- **Model Type**: {'Hammer (Tool)' if hammer_model else 'Chat'}"""
        else:
            calib_section = "- Calibration: AutoAWQ default pipeline"
            
        # Generate README
        quant_summary = json.dumps(quant_config, indent=2)
        readme_contents = generate_readme(
            model_path=model_path,
            awq_version=awq_version,
            quant_summary=quant_summary,
            metadata=metadata,
            calib_section=calib_section,
            out_dir=output_dir
        )
        
        # Save README
        readme_path = os.path.join(output_dir, "README.md")
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_contents)
        except Exception as exc:
            print(f"[awq] Warning: failed to write README ({exc})")
            
        # Create completion marker
        marker = os.path.join(output_dir, ".awq_ok")
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write("ok")
        except Exception:
            pass
