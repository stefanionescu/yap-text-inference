from pathlib import Path


def clean_dir(path: Path) -> None:
    """Remove a directory tree if it exists (best-effort)."""
    if path.exists():
        import contextlib

        for p in sorted(path.rglob("*"), reverse=True):
            with contextlib.suppress(Exception):
                if p.is_file():
                    p.unlink()
                else:
                    p.rmdir()
        with contextlib.suppress(Exception):
            path.rmdir()


def _copy_tree(src: Path, dst: Path) -> None:
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            dest = dst / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())


def _copy_tokenizers(tokenizer_src: Path, repo_root: Path) -> None:
    for name in [
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
        "special_tokens_map.json",
    ]:
        src = tokenizer_src / name
        if src.exists():
            dst = repo_root / name
            dst.write_bytes(src.read_bytes())


def _write_lfs_attributes(repo_root: Path) -> None:
    (repo_root / ".gitattributes").write_text(
        """*.engine filter=lfs diff=lfs merge=lfs -text
*.plan   filter=lfs diff=lfs merge=lfs -text
*.safetensors filter=lfs diff=lfs merge=lfs -text
*.bin    filter=lfs diff=lfs merge=lfs -text
"""
    )


def build_staging_tree(
    repo_root: Path,
    tokenizer_src: Path | None,
    checkpoint_src: Path | None,
    engine_src: Path | None,
    engine_label: str,
) -> None:
    """Create the expected TRT-LLM repository layout in repo_root."""
    (repo_root / "trt-llm").mkdir(parents=True, exist_ok=True)
    (repo_root / "trt-llm" / "checkpoints").mkdir(parents=True, exist_ok=True)
    (repo_root / "trt-llm" / "engines" / engine_label).mkdir(parents=True, exist_ok=True)

    if tokenizer_src and tokenizer_src.is_dir():
        _copy_tokenizers(tokenizer_src, repo_root)

    if checkpoint_src and checkpoint_src.is_dir():
        _copy_tree(checkpoint_src, repo_root / "trt-llm" / "checkpoints")

    if engine_src and engine_src.is_dir():
        _copy_tree(engine_src, repo_root / "trt-llm" / "engines" / engine_label)

    _write_lfs_attributes(repo_root)
