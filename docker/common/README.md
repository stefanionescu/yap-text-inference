# Shared Docker Utilities

Single source of truth for Docker stacks (`vllm`, `trt`, `tool`).
Docker runtime/build scripts are self-contained under `docker/` and reuse this
shared layer directly.

## Contents

- [Scripts](#scripts)
- [Download Utilities](#download-utilities)

## Scripts

### Logging (`scripts/logs.sh`)

Shared log helpers:
- `log_info`
- `log_warn`
- `log_err`
- `log_success`

### Warmup (`scripts/warmup.sh`)

Shared health polling used by all stacks.

Environment variables:
- `WARMUP_MAX_WAIT` (default: `300`)
- `WARMUP_WAIT_INTERVAL` (default: `5`)

### GPU Detection (`scripts/gpu.sh`)

Shared GPU detection helpers:
- `gpu_detect_sm_arch`
- `gpu_detect_name`
- `gpu_detect_vram_gb`
- `gpu_supports_fp8`
- `gpu_init_detection`
- `gpu_apply_env_defaults`

### Deploy Mode (`scripts/deploy_mode.sh`)

Shared deploy mode helpers:
- `normalize_deploy_mode`
- `set_deploy_flags`
- `validate_deploy_models`
- `init_deploy_mode`

### Lifecycle (`scripts/lifecycle.sh`)

Shared container main flow (`run_docker_main`):
- Handles `--help` dispatch
- Sources stack bootstrap script
- Enforces required runtime env (`TEXT_API_KEY`)
- Starts server in either:
  - `direct_common` mode (common server path)
  - `script` mode (stack-specific start script)

### Server Startup (`scripts/server.sh`)

Shared server launch path:
- Resolves uvicorn command
- Starts server process
- Runs warmup health probe

### Build Utilities (`scripts/build/`)

- `args.sh`: initializes Docker build flags
- `docker.sh`: Docker helpers (`require_docker`, `ensure_docker_login`)
- `context.sh`: shared build-context construction (`prepare_build_context_common`)
- `validate.sh`: shared model validation wrapper (`validate_models_for_deploy_common`)

## Download Utilities

### Shared Utils (`download/utils.py`)

Common download helpers:
- `get_hf_token()`
- `download_snapshot()`
- `verify_files_exist()`
- `log_success()`, `log_skip()`

### Tool Model (`download/tool.py`)

Downloads tool model artifacts for all stacks.

Env vars: `TOOL_MODEL`, `TOOL_MODEL_PATH`, `HF_TOKEN`

### Validation (`download/validate.py`)

Strict model validation using `src/config` as source of truth:
- Chat model allowlist/local-path policy per engine
- Tool model allowlist/local-path policy
- TRT engine repo and label format validation

Usage: `python validate.py` (reads env vars)
