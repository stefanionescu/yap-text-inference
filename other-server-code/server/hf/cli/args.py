import argparse
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload TRT-LLM artifacts to Hugging Face")
    parser.add_argument(
        "--repo-id",
        default=os.getenv("HF_PUSH_REPO_ID", ""),
        help="HF repo id, e.g. your-org/my-model-trtllm. If omitted, a default name is generated.",
    )
    parser.add_argument("--private", action="store_true", help="Create as private repo")
    parser.add_argument("--what", choices=["engines", "checkpoints", "both"], default="both", help="What to upload")
    parser.add_argument("--checkpoint-dir", default=os.getenv("CHECKPOINT_DIR"))
    parser.add_argument("--engine-dir", default=os.getenv("TRTLLM_ENGINE_DIR"))
    parser.add_argument("--tokenizer-dir", default=os.getenv("MODEL_ID"))
    parser.add_argument("--engine-label", default=os.getenv("HF_PUSH_ENGINE_LABEL", ""))
    parser.add_argument("--workdir", default=".hf_upload_staging")
    parser.add_argument("--no-readme", action="store_true", help="Do not generate README.md in repo")
    parser.add_argument("--prune", action="store_true", help="Delete matching remote files before upload")
    return parser.parse_args()
