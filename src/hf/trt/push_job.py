"""Push job orchestration for TRT uploads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.config.quantization import CHAT_TEMPLATE_FILES, TOKENIZER_FILES

from src.quantization.trt import collect_metadata, detect_base_model, get_engine_label
from src.hf import create_repo_if_needed
from .readme_renderer import render_trt_readme
from .tokenizer_discovery import find_tokenizer_dir

if TYPE_CHECKING:  # pragma: no cover - optional dependency
    from huggingface_hub import HfApi

__all__ = ["TRTPushJob"]

_HF_CHECKPOINTS_PATH = "trt-llm/checkpoints"
_HF_ENGINES_PATH_FMT = "trt-llm/engines/{engine_label}"


@dataclass
class TRTPushJob:
    """Encapsulates the TRT checkpoint+engine push workflow for testability."""

    api: HfApi
    repo_id: str
    token: str
    branch: str
    checkpoint_path: Path
    engine_path: Path
    engine_provided: bool
    base_model: str | None
    quant_method: str
    private: bool

    def run(self) -> bool:
        if not self.checkpoint_path.is_dir():
            print(f"[trt-hf] Error: Checkpoint directory not found: {self.checkpoint_path}")
            return False

        resolved_base_model = self.base_model or detect_base_model(self.checkpoint_path)
        metadata = collect_metadata(
            self.checkpoint_path,
            self.engine_path,
            resolved_base_model,
            self.repo_id,
            self.quant_method,
        )

        staging_dir = self.checkpoint_path.parent / ".hf_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)

        create_repo_if_needed(self.api, self.repo_id, self.token, self.private)
        self._upload_readme(metadata, staging_dir)
        self._upload_checkpoint()
        self._upload_engine()

        tokenizer_dir = find_tokenizer_dir(self.checkpoint_path, resolved_base_model)
        self._upload_tokenizer(tokenizer_dir)
        self._upload_chat_assets([d for d in [tokenizer_dir, self.checkpoint_path] if d])
        print(f"[trt-hf] ✓ Push complete: {self.repo_id}")
        return True

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------
    def _upload_file(self, src: Path, dest: str) -> bool:
        try:
            self.api.upload_file(
                path_or_fileobj=str(src),
                path_in_repo=dest,
                repo_id=self.repo_id,
                token=self.token,
                revision=self.branch,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[trt-hf] Warning: Failed to upload {dest}: {exc}")
            return False

    def _upload_readme(self, metadata: dict, staging_dir: Path) -> None:
        readme_content = render_trt_readme(metadata)
        readme_path = staging_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        self._upload_file(readme_path, "README.md")

    def _upload_checkpoint(self) -> None:
        print("[trt-hf] Uploading checkpoint...")
        self.api.upload_folder(
            folder_path=str(self.checkpoint_path),
            path_in_repo=_HF_CHECKPOINTS_PATH,
            repo_id=self.repo_id,
            token=self.token,
            revision=self.branch,
        )

    def _upload_engine(self) -> None:
        if not self.engine_provided or not self.engine_path.is_dir():
            return

        engine_label = get_engine_label(self.engine_path)
        engines_path = _HF_ENGINES_PATH_FMT.format(engine_label=engine_label)
        print("[trt-hf] Uploading engines...")

        try:
            self.api.upload_folder(
                folder_path=str(self.engine_path),
                path_in_repo=engines_path,
                repo_id=self.repo_id,
                token=self.token,
                revision=self.branch,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[trt-hf] Error: Failed to upload engine: {exc}")

    def _upload_tokenizer(self, tokenizer_dir: Path | None) -> None:
        if not tokenizer_dir:
            print(
                "[trt-hf] Warning: Tokenizer not found; TRT-LLM will download from base model at runtime"
            )
            return

        print("[trt-hf] Uploading tokenizer...")
        for filename in TOKENIZER_FILES:
            src_file = tokenizer_dir / filename
            if src_file.exists():
                self._upload_file(src_file, filename)

    def _upload_chat_assets(self, candidate_dirs: list[Path]) -> None:
        uploaded = 0
        tried_dirs: set[Path] = set()

        for directory in candidate_dirs:
            if not directory or directory in tried_dirs:
                continue
            tried_dirs.add(directory)

            for filename in CHAT_TEMPLATE_FILES:
                src = directory / filename
                if src.exists() and self._upload_file(src, filename):
                    uploaded += 1

        if uploaded > 0:
            print("[trt-hf] ✓ Uploaded chat template assets")
        else:
            print("[trt-hf] No chat template/generation_config files found. Skipping")
