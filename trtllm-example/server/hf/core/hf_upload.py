from pathlib import Path

from huggingface_hub import create_repo, upload_folder


def create_or_get_repo(repo_id: str, private: bool) -> None:
    create_repo(repo_id, repo_type="model", exist_ok=True, private=private)


def build_delete_patterns(what: str, engine_label: str) -> list[str] | None:
    patterns: list[str] = []
    if what in ("engines", "both"):
        patterns.append(f"trt-llm/engines/{engine_label}/**")
    if what in ("checkpoints", "both"):
        patterns.append("trt-llm/checkpoints/**")
    return patterns or None


def upload_staging_folder(  # noqa: PLR0913
    repo_id: str,
    staging: Path,
    what: str,
    engine_label: str,
    commit_message: str,
    prune: bool,
) -> None:
    delete_patterns = build_delete_patterns(what, engine_label) if prune else None
    upload_folder(
        repo_id=repo_id,
        repo_type="model",
        folder_path=str(staging),
        allow_patterns=["*"],
        delete_patterns=delete_patterns,
        commit_message=commit_message,
    )
