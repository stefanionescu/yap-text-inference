# Multi-stage build for efficient Docker image
# CUDA 13.0 with Ubuntu 24.04 for VLLM 0.13.0 compatibility

FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04 AS builder

# Allow overriding FlashInfer version at build time
ARG FLASHINFER_VERSION_SPEC="==0.5.3"
ARG LLMCOMPRESSOR_VERSION="0.8.1"
ENV FLASHINFER_VERSION_SPEC=${FLASHINFER_VERSION_SPEC}
ENV LLMCOMPRESSOR_VERSION=${LLMCOMPRESSOR_VERSION}

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
ENV FORCE_CUDA=1
ENV MAX_JOBS=8

# Install system dependencies (Ubuntu 24.04 uses python3.12 by default, but we install 3.11 for compatibility)
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    ca-certificates \
    git \
    wget \
    curl \
    gcc \
    g++ \
    make \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
# Install all requirements except flashinfer-python first, mirroring the scripts install flow
RUN set -eux; \
    export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1 PIP_PREFER_BINARY=1 FLASHINFER_ENABLE_AOT=1; \
    TMP_REQ=/tmp/requirements.no_flashinfer.txt; \
    grep -v -E '^[[:space:]]*(flashinfer-python|llmcompressor)([[:space:]]|$|==|>=|<=|~=|!=)' /tmp/requirements.txt > "${TMP_REQ}" || cp /tmp/requirements.txt "${TMP_REQ}" || true; \
    pip install --no-cache-dir -r "${TMP_REQ}"; \
    CUDA_NVVER="$(python -c 'import sys, torch; cu=(torch.version.cuda or "").strip(); sys.exit(1) if not cu else print(cu.replace(".", ""))' 2>/dev/null || true)"; \
    TORCH_MAJMIN="$(python -c 'import sys, torch; ver=torch.__version__.split("+",1)[0]; p=ver.split("."); print(p[0]+"."+p[1])' 2>/dev/null || true)"; \
    if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then \
        FI_IDX="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.3}"; \
        echo "[build] Installing ${FI_PKG} from ${FI_IDX}"; \
        pip install --no-cache-dir --prefer-binary --extra-index-url "${FI_IDX}" "${FI_PKG}" || \
        (echo "[build] FlashInfer install via extra index failed, falling back to PyPI" && pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true); \
    else \
        echo "[build] Torch/CUDA not detected at build-time; attempting PyPI install for FlashInfer with version spec"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.3}"; \
        pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true; \
    fi; \
    if [ -n "${LLMCOMPRESSOR_VERSION:-}" ]; then \
        echo "[build] Installing llmcompressor without deps"; \
        pip install --no-cache-dir --no-deps "llmcompressor==${LLMCOMPRESSOR_VERSION}"; \
    fi

# =============================================================================
# Production stage
# =============================================================================
FROM nvidia/cuda:13.0.0-cudnn-runtime-ubuntu24.04

# Model configuration - set and downloaded at build time
ARG DEPLOY_MODE="both"
ARG CHAT_MODEL=""
ARG TOOL_MODEL=""

# HuggingFace token for private repos
ARG HF_TOKEN=""

# Set environment variables for production
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# Configured models - these are set at build time
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV CHAT_MODEL=${CHAT_MODEL}
ENV TOOL_MODEL=${TOOL_MODEL}

# Engine type for vLLM
ENV INFERENCE_ENGINE=vllm

# Default directories for baked-in models
ENV MODELS_DIR=/opt/models
ENV CHAT_MODEL_PATH=/opt/models/chat
ENV TOOL_MODEL_PATH=/opt/models/tool

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code from build context
COPY src/ /app/src/
COPY scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/.run /app/.hf /app/.vllm_cache /opt/models

# Set proper permissions
RUN chmod +x /app/scripts/*.sh

# Cache directories
ENV HF_HOME=/app/.hf
ENV HUGGINGFACE_HUB_CACHE=/app/.hf/hub
ENV VLLM_CACHE_DIR=/app/.vllm_cache
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# ----------------------------------------------------------------------------
# Download pre-quantized chat model at build time (baked into image)
# This makes startup instant - no downloads needed at runtime!
# ----------------------------------------------------------------------------
RUN --mount=type=secret,id=hf_token,required=false \
    set -eux; \
    if [ -n "${CHAT_MODEL}" ]; then \
        echo "[build] Downloading pre-quantized chat model..."; \
        echo "[build]   Model: ${CHAT_MODEL}"; \
        HF_TOKEN_VAL=""; \
        if [ -f /run/secrets/hf_token ]; then \
            HF_TOKEN_VAL=$(cat /run/secrets/hf_token); \
        fi; \
        python -c " \
import os, sys \
from huggingface_hub import snapshot_download \
\
repo_id = '${CHAT_MODEL}' \
target_dir = '/opt/models/chat' \
token = os.environ.get('HF_TOKEN') or '${HF_TOKEN}' or None \
if token == '': token = None \
\
print(f'[build] Downloading {repo_id}...') \
try: \
    snapshot_download( \
        repo_id=repo_id, \
        local_dir=target_dir, \
        token=token, \
    ) \
    print('[build] ✓ Chat model downloaded and baked into image') \
except Exception as e: \
    print(f'[build] ERROR: Failed to download chat model: {e}', file=sys.stderr) \
    sys.exit(1) \
"; \
    else \
        echo "[build] No CHAT_MODEL specified - skipping chat model download"; \
    fi

# Download tool model at build time if specified
RUN --mount=type=secret,id=hf_token,required=false \
    set -eux; \
    if [ -n "${TOOL_MODEL}" ]; then \
        echo "[build] Downloading tool model..."; \
        echo "[build]   Model: ${TOOL_MODEL}"; \
        HF_TOKEN_VAL=""; \
        if [ -f /run/secrets/hf_token ]; then \
            HF_TOKEN_VAL=$(cat /run/secrets/hf_token); \
        fi; \
        python -c " \
import os, sys \
from huggingface_hub import snapshot_download \
\
repo_id = '${TOOL_MODEL}' \
target_dir = '/opt/models/tool' \
token = os.environ.get('HF_TOKEN') or '${HF_TOKEN}' or None \
if token == '': token = None \
\
print(f'[build] Downloading {repo_id}...') \
try: \
    snapshot_download( \
        repo_id=repo_id, \
        local_dir=target_dir, \
        token=token, \
    ) \
    print('[build] ✓ Tool model downloaded and baked into image') \
except Exception as e: \
    print(f'[build] ERROR: Failed to download tool model: {e}', file=sys.stderr) \
    sys.exit(1) \
"; \
    else \
        echo "[build] No TOOL_MODEL specified - skipping tool model download"; \
    fi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["/app/scripts/main.sh"]

