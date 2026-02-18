# Shared Docker Utilities

Single source of truth for Docker stacks (`vllm`, `trt`, `tool`). Docker runtime/build scripts are self-contained under `docker/` and reuse this shared layer directly.

## Contents

- [Script Architecture](#script-architecture)
- [Scripts](#scripts)
- [Download Utilities](#download-utilities)
- [Integration Flow](#integration-flow)

## Script Architecture

Docker scripting is self-contained under `docker/`:
- Shared Docker logic lives in `docker/common/`.
- Stack directories (`docker/vllm`, `docker/trt`, `docker/tool`) keep only stack-specific behavior.
- Runtime scripts do not source host orchestration scripts under repo root `scripts/`.
- Avoid pass-through wrappers; source common scripts directly when behavior is shared.

## Scripts

### Logging (`scripts/logs.sh`)

Consistent log output formatting across all build and runtime scripts.

- `log_info` -- general informational output
- `log_warn` -- non-fatal warnings
- `log_err` -- fatal error output
- `log_success` -- success confirmation
- `log_section` -- blank line followed by info log (visual separator)

### Warmup (`scripts/warmup.sh`)

Polls the server health endpoint until the inference backend is ready, used by all stacks at container startup.

Environment variables:
- `WARMUP_MAX_WAIT` (default: `300`) -- seconds before giving up
- `WARMUP_WAIT_INTERVAL` (default: `5`) -- seconds between polls

### GPU Detection (`scripts/gpu.sh`)

Auto-detects GPU architecture and applies engine-specific defaults at container startup.

- `gpu_detect_sm_arch` -- returns `sm80`, `sm89`, `sm90`, etc. (prefers `nvidia-smi` compute_cap, falls back to name mapping)
- `gpu_detect_name` -- returns human-readable GPU name (e.g., `NVIDIA H100`)
- `gpu_detect_vram_gb` -- returns total VRAM in GB
- `gpu_supports_fp8` -- returns 0 (true) for sm89/sm90 (Ada Lovelace, Hopper)
- `gpu_init_detection` -- detects and exports `GPU_SM_ARCH` and `DETECTED_GPU_NAME`
- `gpu_apply_env_defaults` -- sets `TORCH_CUDA_ARCH_LIST`, `PYTORCH_ALLOC_CONF`, and GPU-family optimizations

### Deploy Mode (`scripts/deploy_mode.sh`)

Parses and validates the deploy mode (`chat`, `tool`, `both`) and sets convenience flags consumed by bootstrap scripts.

- `normalize_deploy_mode` -- validates `DEPLOY_MODE`, defaults to `both`
- `set_deploy_flags` -- exports `DEPLOY_CHAT` and `DEPLOY_TOOL` (0 or 1)
- `validate_deploy_models` -- fails if required model env vars are missing for the deploy mode
- `init_deploy_mode` -- runs all three steps in order (normalize, flags, validate)

### Lifecycle (`scripts/lifecycle.sh`)

Shared container main flow (`run_docker_main`) that keeps stack `main.sh` scripts thin while preserving stack-specific usage text.

- Handles `--help` dispatch to stack-specific usage function
- Sources the stack's `bootstrap.sh` to configure environment
- Enforces required runtime env (`TEXT_API_KEY`)
- Starts server in either:
  - `direct_common` mode -- launches uvicorn via the shared server path
  - `script` mode -- execs a stack-specific start script (used by TRT)

### Server Startup (`scripts/server.sh`)

One canonical server launch path shared by all stacks.

- `resolve_uvicorn_cmd` -- finds a working uvicorn binary (direct, `python -m`, or `python3 -m`)
- `start_server_with_warmup` -- starts uvicorn in the background, runs warmup health probe, then waits on the server process

### Build Utilities (`scripts/build/`)

Host-side helpers sourced by each stack's `build.sh`.

- `args.sh` / `init_build_args` -- initializes the `BUILD_ARGS` array with `--file`, `--tag`, `--platform`
- `docker.sh` / `require_docker` -- checks Docker daemon is running; `ensure_docker_login` -- logs in via `DOCKER_PASSWORD` or `DOCKER_TOKEN`
- `context.sh` / `prepare_build_context_common` -- creates a temp directory with only the runtime assets needed by the Dockerfile
- `validate.sh` / `validate_models_for_deploy_common` -- runs `docker/common/download/validate.py` to enforce model allowlists and engine label format

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

## Integration Flow

### Build Time

1. User runs `docker/build.sh` with `ENGINE` and `DEPLOY_MODE`.
2. Top-level script validates the tag prefix and routes to the engine-specific `docker/{engine}/build.sh` (tool-only routes to `docker/tool/build.sh`).
3. Engine build script sources common build utilities (`args.sh`, `docker.sh`, `context.sh`, `validate.sh`).
4. `validate_models_for_deploy_common` calls `docker/common/download/validate.py` to check model allowlists.
5. `prepare_build_context_common` assembles a temp directory with `src/`, stack scripts, common scripts, and download scripts.
6. Docker builds the image, running download scripts inside the Dockerfile to bake models/engines in.

### Runtime

1. Container starts at the stack's `main.sh` entrypoint.
2. `main.sh` calls `run_docker_main` (from `common/scripts/lifecycle.sh`).
3. Lifecycle sources the stack's `bootstrap.sh`, which:
   - Sources `common/scripts/logs.sh` and `common/scripts/deploy_mode.sh`
   - Calls `init_deploy_mode` to set flags
   - Sources stack-specific env scripts (GPU detection, runtime defaults)
4. Lifecycle enforces `TEXT_API_KEY`, then either launches the shared server path (`direct_common`) or execs the stack's `start_server.sh` (`script` mode).
5. Warmup script polls `/healthz` until the backend is ready.
