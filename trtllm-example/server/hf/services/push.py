import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

try:
    from ..core.hf_upload import create_or_get_repo, upload_staging_folder
    from ..core.metadata import collect_env_metadata, derive_hardware_labels, detect_engine_label
    from ..core.staging import build_staging_tree, clean_dir
    from ..readme.renderer import write_readme
    from ..readme.utils import source_model_from_env_or_meta
except Exception:
    # direct execution path support
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from server.hf.core.hf_upload import create_or_get_repo, upload_staging_folder
    from server.hf.core.metadata import collect_env_metadata, derive_hardware_labels, detect_engine_label
    from server.hf.core.staging import build_staging_tree, clean_dir
    from server.hf.readme.renderer import write_readme
    from server.hf.readme.utils import source_model_from_env_or_meta


def resolve_paths(args):
    checkpoint_dir = Path(args.checkpoint_dir) if args.checkpoint_dir else None
    engine_dir = Path(args.engine_dir) if args.engine_dir else None
    tokenizer_dir = Path(args.tokenizer_dir) if args.tokenizer_dir and os.path.isdir(args.tokenizer_dir) else None
    return checkpoint_dir, engine_dir, tokenizer_dir


def validate_inputs(what: str, checkpoint_dir: Path | None, engine_dir: Path | None) -> None:
    if what in ("checkpoints", "both") and not (checkpoint_dir and checkpoint_dir.is_dir()):
        print(f"[push] ERROR: checkpoint dir not found: {checkpoint_dir}", file=sys.stderr)
        sys.exit(1)
    if what in ("engines", "both") and not (engine_dir and engine_dir.is_dir()):
        print(f"[push] ERROR: engine dir not found: {engine_dir}", file=sys.stderr)
        sys.exit(1)


def run_push(args) -> None:
    # surface auth issues early
    _ = HfApi()

    checkpoint_dir, engine_dir, tokenizer_dir = resolve_paths(args)
    validate_inputs(args.what, checkpoint_dir, engine_dir)

    engine_label = detect_engine_label(engine_dir or Path("."), args.engine_label or None)

    # Collect metadata to derive defaults (e.g., hardware and base model)
    meta = collect_env_metadata(engine_dir or Path("."))
    precision_mode = (os.environ.get("ORPHEUS_PRECISION_MODE") or meta.get("precision_mode") or "").lower()
    quant_weights = ((meta.get("quantization") or {}).get("weights") or "").lower()
    normalized_weights = quant_weights.replace("-", "_")
    allowed_quant = {"int4_awq", "int4awq"}
    if precision_mode and precision_mode != "quantized":
        print(
            "[push] ERROR: Hugging Face uploads are restricted to INT4-AWQ builds (precision_mode != quantized).",
            file=sys.stderr,
        )
        sys.exit(1)
    if normalized_weights and normalized_weights not in allowed_quant:
        print(f"[push] ERROR: Detected weights '{quant_weights}' are not INT4-AWQ; aborting push.", file=sys.stderr)
        sys.exit(1)
    if not (getattr(args, "repo_id", None) or ""):
        base_model = source_model_from_env_or_meta(meta)
        base_slug = (base_model or "").split("/")[-1].lower().replace("_", "-")
        hw_slug, _hw_pretty = derive_hardware_labels(meta)
        # Default repo name: <base>-int4-awq-<hardware>
        default_name = f"{base_slug}-int4-awq-{hw_slug}"
        # Avoid accidental double dashes
        default_name = "-".join(filter(None, default_name.split("-")))
        args.repo_id = default_name
        print(f"[push] No repo id provided; using default name: {args.repo_id}")

    staging = Path(args.workdir)
    clean_dir(staging)
    staging.mkdir(parents=True, exist_ok=True)

    build_staging_tree(
        repo_root=staging,
        tokenizer_src=tokenizer_dir,
        checkpoint_src=checkpoint_dir if args.what in ("checkpoints", "both") else None,
        engine_src=engine_dir if args.what in ("engines", "both") else None,
        engine_label=engine_label,
    )

    create_or_get_repo(args.repo_id, private=args.private)

    if not args.no_readme:
        write_readme(staging, engine_label, meta, args.what, args.repo_id)

    commit_msg = f"Upload TRT-LLM {args.what} (engine_label={engine_label})"

    print(f"[push] Uploading folder {staging} to {args.repo_id}...")
    upload_staging_folder(
        repo_id=args.repo_id,
        staging=staging,
        what=args.what,
        engine_label=engine_label,
        commit_message=commit_msg,
        prune=args.prune,
    )
    print("[push] Upload complete.")
