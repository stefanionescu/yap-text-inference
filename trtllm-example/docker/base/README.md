# Orpheus TensorRT Base Image (CUDA 13.0, Torch 2.9.1 cu130)

Large (~100GB) image for research/experimentation and quantization workflows. Not for production use. Use the fast image for runtime serving.

## Contents

- [Purpose](#purpose)
- [What's Included](#whats-included)
- [Build](#build)
- [Precision Mode](#precision-mode)
- [Runtime Examples](#runtime-examples)
- [Testing](#testing)

## Purpose

- Explore/iterate on Orpheus quantization with TensorRT-LLM
- Build engines with different parameters
- Start the API server for validation after a build

## What's Included

- CUDA 13.0.0 cudnn-devel (Ubuntu 24.04), Python 3.10 venv
- PyTorch 2.9.1 + torchvision 0.24.1 (cu130 wheels)
- TensorRT-LLM 1.2.0rc5 wheel (NVIDIA PyPI); TRT-LLM repo cloned and version-synced in `/opt/TensorRT-LLM`
- Uses system CUDA libraries only (no pip-provided CUDA runtimes)
- App code `/app/server/` and `/app/tests/`
- Runtime scripts in `/usr/local/bin`:
  - `01-quantize-and-build.sh`: INT4-AWQ + engine build
  - `02-start-server.sh`: start FastAPI server
  - `run.sh`: orchestrate build → server
- Environment defaults auto-sourced from `docker/base/scripts/environment.sh`

## Build

```bash
cd /path/to/yap-orpheus-tts-api
export HF_TOKEN=hf_xxx                   # optional at build time (as BuildKit secret)
DOCKER_BUILDKIT=1 bash docker/base/build.sh

# Overrides (optional; cu130 default for TRT-LLM 1.2.0rc5)
PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 \
TRTLLM_PIP_SPEC="tensorrt_llm==1.2.0rc5" \
IMAGE_NAME=sionescu/orpheus-trtllm-base IMAGE_TAG=cu130-py311-trt1.2 \
bash docker/base/build.sh
```

Notes:
- `HF_TOKEN` (when provided) is passed as a BuildKit secret and not persisted.
- Provide secrets at build via `--secret` or at runtime via `-e`.

## Precision Mode

- `ORPHEUS_PRECISION_MODE=quantized|base` mirrors the repo scripts. Quantized (default) runs INT4-AWQ + INT8 KV cache. Base mode keeps HF weights and builds FP16/FP8 engines.
- Base mode auto-picks FP16 on Ampere (A100) and FP8 (`fp8_e4m3`) on Ada/Hopper (L40/H100/etc.). Override with `BASE_INFERENCE_DTYPE`.
- The default engine/checkpoint paths switch automatically (`/opt/engines/orpheus-trt-awq` vs `/opt/engines/orpheus-trt-base`), so no manual tweaking is needed unless you specify your own directories.

## Runtime Examples

Quantize → build → start server (background):
```bash
docker run --gpus all --rm \
  -e HF_TOKEN=$HF_TOKEN \
  -e ORPHEUS_API_KEY=your_secret_key \
  -e MODEL_PRESET=canopy \  # default is 'canopy'; set 'fast' to use the fast model (or set MODEL_ID)
  -e ORPHEUS_PRECISION_MODE=quantized \
  -e TRTLLM_ENGINE_DIR=/opt/engines/orpheus-trt-awq \
  -v /path/for/engines:/opt/engines \
  -p 8000:8000 \
  -it IMAGE:TAG run.sh
```

Base-mode example (auto FP8/FP16 selection; override dtype if desired):

```bash
docker run --gpus all --rm \
  -e HF_TOKEN=$HF_TOKEN \
  -e ORPHEUS_API_KEY=your_secret_key \
  -e ORPHEUS_PRECISION_MODE=base \
  -e BASE_INFERENCE_DTYPE=float16 \  # optional; omit to auto-detect
  -e TRTLLM_ENGINE_DIR=/opt/engines/orpheus-trt-base \
  -v /path/for/engines:/opt/engines \
  -p 8000:8000 \
  -it IMAGE:TAG run.sh
```

Build engine only:
```bash
docker run --gpus all --rm \
  -e HF_TOKEN=$HF_TOKEN \
  -e MODEL_PRESET=canopy \
  -e ORPHEUS_PRECISION_MODE=quantized \
  -v /path/for/engines:/opt/engines \
  -it IMAGE:TAG 01-quantize-and-build.sh --engine-dir /opt/engines/orpheus-trt-awq
```

Start server (engine already present):
```bash
docker run --gpus all --rm \
  -e HF_TOKEN=$HF_TOKEN \
  -e ORPHEUS_API_KEY=your_secret_key \
  -e TRTLLM_ENGINE_DIR=/opt/engines/orpheus-trt-awq \
  -p 8000:8000 -it IMAGE:TAG 02-start-server.sh
```

Ensure the host runtime provides NVIDIA GPU access (`--gpus all`). This image relies on the system CUDA from the base (no pip CUDA libs), matching the custom stack.

Note:
- Default preset is `canopy` (uses `yapwithai/canopy-orpheus-3b-0.1-ft`). Set `MODEL_PRESET=fast` to use `yapwithai/fast-orpheus-3b-0.1-ft`.
- Alternatively, set `MODEL_ID=yapwithai/fast-orpheus-3b-0.1-ft` (or the canopy model) to override the preset.
- When using base mode, set/keep `TRTLLM_ENGINE_DIR=/opt/engines/orpheus-trt-base` (shared volume path mirrors this).

## Testing

Inside the container (after server is running):
```bash
python /app/tests/warmup.py --server 127.0.0.1:8000 --voice female
python /app/tests/bench.py --n 8 --concurrency 8
```
