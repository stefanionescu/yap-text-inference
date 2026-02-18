# Shared Docker Utilities

Scripts and utilities shared between TRT and vLLM Docker images.

## Contents

- [Scripts](#scripts)
- [Download Utilities](#download-utilities)

## Scripts

### Logging (`scripts/logs.sh`)

Logging functions aligned with `scripts/lib/common/log.sh`:
- `log_info` - Standard info messages
- `log_warn` - Warning messages  
- `log_err` - Error messages
- `log_success` - Success messages

### Warmup (`scripts/warmup.sh`)

Waits for server health and exits.

Features:
- Health check polling with configurable timeout
- No test-client execution inside Docker

Environment variables:
- `WARMUP_MAX_WAIT` - Max seconds to wait for health (default: 300)
- `WARMUP_WAIT_INTERVAL` - Sleep interval between checks (default: 5)

### GPU Detection (`scripts/gpu_detect.sh`)

Unified GPU detection mirroring `scripts/lib/common/gpu_detect.sh`:
- `gpu_detect_sm_arch` - Get SM architecture (e.g., sm90)
- `gpu_detect_name` - Get GPU name
- `gpu_detect_vram_gb` - Get VRAM in GB
- `gpu_supports_fp8` - Check FP8 support
- `gpu_init_detection` - Initialize and export GPU vars
- `gpu_apply_env_defaults` - Set GPU-specific env vars

### Deploy Mode (`scripts/deploy_mode.sh`)

Shared deploy mode handling:
- `normalize_deploy_mode` - Validate DEPLOY_MODE
- `set_deploy_flags` - Set DEPLOY_CHAT/DEPLOY_TOOL flags
- `validate_deploy_models` - Check required models
- `init_deploy_mode` - Initialize all deploy config

### Build Utilities (`scripts/build/`)

- `args.sh` - Initializes Docker build flags
- `docker.sh` - Docker helpers (`require_docker`, `ensure_docker_login`)

## Download Utilities

### Shared Utils (`download/utils.py`)

Common download functionality:
- `get_hf_token()` - Get HuggingFace token from env or secret
- `download_snapshot()` - Download from HuggingFace with patterns
- `verify_files_exist()` - Validate downloaded files
- `log_success()`, `log_skip()` - Logging helpers

### Tool Model (`download/tool.py`)

Downloads the tool model from HuggingFace. Used by both engines.

Env vars: `TOOL_MODEL`, `TOOL_MODEL_PATH`, `HF_TOKEN`

### Validation (`download/validate.py`)

Model validation using `src/config` as source of truth:
- Validates chat model pre-quantization markers
- Validates tool model against allowlist
- Validates TRT engine repo and label format

Usage: `python validate.py` (reads from env vars)
