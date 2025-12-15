# Orpheus TTS AWQ Image

Lean, production-focused image. Pulls a pre-quantized Orpheus checkpoint or prebuilt engines from Hugging Face (or mounts a local engine), validates, optionally builds the engine with `trtllm-build`, then runs the API server.

## Contents

- [What's Included](#whats-included)
- [Build](#build)
- [Run](#run)
- [Environment Variables](#environment-variables)
- [Logs](#logs)
- [Testing Inside the Container](#testing-inside-the-container)

## What's Included

- CUDA 13.0 runtime + Python 3.10 venv
- PyTorch 2.9.1 + torchvision 0.24.1 (cu130 wheels)
- TensorRT-LLM 1.2.0rc5 runtime wheel (from NVIDIA PyPI; no repo clone)
- App code (`/app/server/`) and tests (`/app/tests/`, minus `client.py`)
- Runtime scripts: `start-server.sh` and `environment.sh`

Not included: engines and models (fetched/mounted at runtime).

## Build

```bash
cd /path/to/yap-orpheus-tts-api
# Basic build
bash docker/awq/build.sh

# Custom name/tag or registry
IMAGE_NAME=myregistry/yap-orpheus-tts-trt-awq IMAGE_TAG=prod \
bash docker/awq/build.sh

# Optional: custom PyTorch/TensorRT versions (cu130 default for TRT-LLM 1.2.0rc5)
PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 \
TRTLLM_PIP_SPEC="tensorrt_llm==1.2.0rc5" \
bash docker/awq/build.sh

# Push in one step
bash docker/awq/build.sh --push

# Or push after build
docker login
docker push ${IMAGE_NAME:-yap-orpheus-trt-tts-api}:${IMAGE_TAG:-latest}
```

> **TensorRT-LLM versioning note:** If you override `TRTLLM_PIP_SPEC`, keep `TRTLLM_TARGET_VERSION`/engine labels in sync.

## Run

Pull engines or a quantized checkpoint from a HF repo created with our tooling. If engines match your GPU/driver, the container skips build; if only checkpoints exist, it builds the engine locally.

```bash
docker run --gpus all --rm -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN \
  -e ORPHEUS_API_KEY=$ORPHEUS_API_KEY \
  -e HF_DEPLOY_REPO_ID=your-org/orpheus-trtllm \
  -e HF_DEPLOY_ENGINE_LABEL=sm80_trt-llm-1.2.0rc5_cuda13.0 \
  IMAGE:TAG
```

Alternate: mount a prebuilt engine directory (no HF pull):

```bash
docker run --gpus all --rm -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN \
  -e ORPHEUS_API_KEY=$ORPHEUS_API_KEY \
  -e TRTLLM_ENGINE_DIR=/opt/engines/orpheus-trt-awq \
  -v /path/to/engine:/opt/engines/orpheus-trt-awq:ro \
  IMAGE:TAG
```

## Environment Variables

- `HF_TOKEN` (required): HF token for repo access
- `ORPHEUS_API_KEY` (optional): API auth for server
- `HF_DEPLOY_REPO_ID` (optional): HF repo to pull from (engines/checkpoints layout)
- `HF_DEPLOY_ENGINE_LABEL` (optional): engines/<label> selector for prebuilt engines
- `HF_DEPLOY_USE` (default: `auto`): `auto|engines|checkpoints`
- `TRTLLM_ENGINE_DIR` (optional): engine dir if mounting locally
- `MODEL_ID` (optional): tokenizer source; used if not provided by HF repo
- `MODELS_DIR` (default: `/opt/models`)
- `ENGINES_DIR` (default: `/opt/engines`)
- `HOST` (default: `0.0.0.0`), `PORT` (default: `8000`)

Advanced knobs (used by server/runtime):
- `TRTLLM_MAX_INPUT_LEN`, `TRTLLM_MAX_OUTPUT_LEN`, `TRTLLM_MAX_BATCH_SIZE`
- `KV_FREE_GPU_FRAC`, `KV_ENABLE_BLOCK_REUSE`
- `ORPHEUS_MAX_TOKENS` (default 1162, ~14 seconds of audio), `DEFAULT_TEMPERATURE`, `DEFAULT_TOP_P`, `DEFAULT_REPETITION_PENALTY`
- `SNAC_SR`, `SNAC_MAX_BATCH`, `SNAC_BATCH_TIMEOUT_MS`, `TTS_DECODE_WINDOW`, `TTS_MAX_SEC`
- `WS_END_SENTINEL`, `WS_CLOSE_BUSY_CODE`, `WS_CLOSE_INTERNAL_CODE`, `WS_QUEUE_MAXSIZE`, `DEFAULT_VOICE`

## Logs

This image writes server logs to `/app/logs/server.log` and tails them to Docker stdout. View them from the host:

```bash
docker logs -f <container_name_or_id>
```

To access the log file directly on the host, bind-mount a directory:

```bash
docker run --gpus all --rm -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN -e ORPHEUS_API_KEY=$ORPHEUS_API_KEY \
  -v "$(pwd)/logs:/app/logs" \
  IMAGE:TAG
```

## Testing Inside the Container

```bash
# Warmup
docker exec -it <container> python /app/tests/warmup.py --server 127.0.0.1:8000 --voice female

# Benchmark
docker exec -it <container> python /app/tests/bench.py --n 10 --concurrency 4
```
