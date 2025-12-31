# TensorRT-LLM Docker Image

TRT-LLM inference image with models baked in.

## Contents

- [Quick Start](#quick-start)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)

## Quick Start

### Build

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_REPO=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:trt-qwen30b-sm90
```

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | HF repo for tokenizer/checkpoint |
| `TRT_ENGINE_REPO` | If chat/both | HF repo with pre-built engines |
| `TRT_ENGINE_LABEL` | If chat/both | Engine directory (e.g., `sm90_trt-llm-0.17.0_cuda12.8`) |
| `TOOL_MODEL` | If tool/both | Tool classifier HF repo |
| `TAG` | Yes | Image tag (must start with `trt-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXT_API_KEY` | Required | API key |
| `TRT_KV_FREE_GPU_FRAC` | 0.90 | GPU fraction for KV cache |
| `TRT_KV_ENABLE_BLOCK_REUSE` | 0 | Enable KV cache block reuse |

