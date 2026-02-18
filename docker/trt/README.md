# TensorRT-LLM Docker Image

TRT-LLM inference image with models baked in. This stack is for TRT chat deployments (`DEPLOY_MODE=chat|both`).

For tool-only images, use `docker/build.sh` with `DEPLOY_MODE=tool` (auto-routes to `docker/tool/build.sh`).

For an overview of all stacks, see the [main Docker README](../README.md).

## Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Engine Label Format](#engine-label-format)
- [GPU Compatibility](#gpu-compatibility)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)
- [Troubleshooting](#troubleshooting)

## How It Works

1. **Build time**: The pre-built TRT engine is downloaded from HuggingFace and baked into the image along with the tokenizer/checkpoint.
2. **Runtime**: The server starts immediately with the baked-in engine -- no compilation at startup.

The tool model always runs as PyTorch (not TRT). For tool-only images, use the [Tool-Only](../tool/README.md) stack.

## Quick Start

### Build (Chat-Only)

> **GPU architecture must match.** TRT engines are compiled for a specific GPU architecture (e.g., sm90 for H100). The engine label must match the GPU you will run on. See [GPU Compatibility](#gpu-compatibility).

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

### Build (Both Models)

TRT chat engine plus PyTorch tool model in a single image:

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=both \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-qwen3-full-sm90 \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -p 8000:8000 \
  myuser/yap-text-api:trt-qwen30b-sm90
```

### Verify

```bash
curl http://localhost:8000/healthz
```

## Engine Label Format

Format: `sm{arch}_trt-llm-{version}_cuda{version}`

The `sm` prefix identifies the GPU compute architecture the engine was compiled for:

| SM Code | GPUs |
|---------|------|
| `sm90` | H100, H200 |
| `sm89` | L40S, L40, RTX 4090/4080/4070 |
| `sm80` | A100, A10, A30, RTX 3090/3080 |

Check your GPU's compute capability:

```bash
nvidia-smi --query-gpu=compute_cap --format=csv,noheader
```

## GPU Compatibility

> **TRT engines are not portable across GPU architectures.** An engine built for sm90 (H100) will not run on sm89 (L40S) or sm80 (A100). Always verify your target GPU before building.

If you deploy to a GPU that does not match the engine label, the container will fail at startup with a `GPU ARCHITECTURE MISMATCH` error. Build a separate image for each GPU architecture you deploy to.

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat` or `both` |
| `CHAT_MODEL` | If chat/both | HF repo for tokenizer/checkpoint |
| `TRT_ENGINE_REPO` | No | HF repo with pre-built engines (defaults to `CHAT_MODEL`) |
| `TRT_ENGINE_LABEL` | If chat/both | Engine directory (e.g., `sm90_trt-llm-0.17.0_cuda12.8`) |
| `TOOL_MODEL` | If both | Tool model HF repo |
| `TAG` | Yes | Image tag (must start with `trt-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEXT_API_KEY` | Yes | - | API key |
| `MAX_CONCURRENT_CONNECTIONS` | Yes | - | Maximum concurrent WebSocket connections |
| `TRT_KV_FREE_GPU_FRAC` | No | 0.90 (single) / 0.70 (both) | GPU fraction for KV cache |
| `TOOL_GPU_FRAC` | No | 0.90 (single) / 0.20 (both) | GPU fraction for tool model |

## Troubleshooting

For common issues (CUDA not available, OOM, large images), see [Troubleshooting](../README.md#troubleshooting) in the main Docker README.

**"GPU ARCHITECTURE MISMATCH"**: The baked-in engine was built for a different GPU. TRT engines are not portable. Check your GPU: `nvidia-smi --query-gpu=compute_cap --format=csv,noheader` and rebuild with the correct `TRT_ENGINE_LABEL`.

**"MISSING ENGINE METADATA"**: The engine directory is missing `build_metadata.json`. Rebuild the TRT engine.

**"CANNOT DETECT RUNTIME GPU"**: Run the container with `--gpus all`.

**"TRT_ENGINE_REPO is not set"**: Set `CHAT_MODEL` (used as default) or `TRT_ENGINE_REPO` explicitly for TRT chat/both builds.

**"TRT_ENGINE_LABEL has invalid format"**: Must match `sm{digits}_trt-llm-{version}_cuda{version}`.

**"No .engine files found"**: Verify the engine exists in the HuggingFace repo under the specified label directory.

**"TAG must start with 'trt-'"**: Tags for TRT images must use the `trt-` prefix (e.g., `trt-qwen30b-sm90`).
