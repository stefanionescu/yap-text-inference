# Shared Docker Utilities

Common scripts and utilities shared between TRT and vLLM Docker images.

## Contents

- [Scripts](#scripts)
- [Download Utilities](#download-utilities)

## Scripts

### logs.sh

Provides consistent logging functions: `log_info`, `log_warn`, `log_error`, `log_success`.

### warmup.sh

Health check script that waits for the server to become healthy. Accepts an engine
prefix as the first argument for log messages:

```bash
./warmup.sh trt    # Logs as [trt-warmup]
./warmup.sh vllm   # Logs as [vllm-warmup]
```

### build/args.sh

Initializes the `BUILD_ARGS` array with common Docker build flags. Requires
`DOCKERFILE`, `FULL_IMAGE_NAME`, and `PLATFORM` to be defined.

### build/docker.sh

Docker helper functions:
- `require_docker`: Verifies Docker is running
- `ensure_docker_login`: Handles Docker Hub authentication

## Download Utilities

### download_tool.py

Downloads the tool classifier model from HuggingFace. Used by both TRT and vLLM
builds since the tool model runs as a standard PyTorch model on both engines.

Environment variables:
- `TOOL_MODEL`: HuggingFace repo ID
- `TOOL_MODEL_PATH`: Target directory (default: `/opt/models/tool`)
- `HF_TOKEN`: Optional token for private repos

