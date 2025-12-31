# Shared Docker Utilities

Scripts shared between TRT and vLLM Docker images.

## Contents

- [Scripts](#scripts)
- [Download Utilities](#download-utilities)

## Scripts

- `logs.sh` - Logging functions (`log_info`, `log_warn`, `log_error`, `log_success`)
- `warmup.sh` - Waits for server health. Usage: `./warmup.sh trt` or `./warmup.sh vllm`
- `build/args.sh` - Initializes Docker build flags
- `build/docker.sh` - Docker helpers (`require_docker`, `ensure_docker_login`)

## Download Utilities

`download_tool.py` - Downloads the tool classifier from HuggingFace. Used by both engines.

Env vars: `TOOL_MODEL`, `TOOL_MODEL_PATH`, `HF_TOKEN`

