# TensorRT-LLM production image for pre-quantized models
# CUDA 13.0 with Ubuntu 24.04 (TRT-LLM 1.2.0rc6 requires torch 2.9.x cu130)
FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04

# Use bash for RUN lines
SHELL ["/bin/bash", "-lc"]

# Non-interactive APT
ENV DEBIAN_FRONTEND=noninteractive

# Model configuration - set at build time
ARG DEPLOY_MODE="both"
ARG CHAT_MODEL=""
ARG TOOL_MODEL=""

# TRT engine configuration - HuggingFace repo with pre-built engines
ARG TRT_ENGINE_REPO=""

# TensorRT-LLM version configuration
ARG TRTLLM_PIP_SPEC=tensorrt_llm==1.2.0rc6
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu130

# MPI runtime pin for TRT-LLM (prevents CUDA downgrade)
ARG MPI_VERSION_PIN=4.1.6-7ubuntu2

# Python version (via deadsnakes PPA)
ENV PYTHON_VERSION=3.10
ENV VENV_DIR=/opt/venv

# ----------------------------------------------------------------------------
# System bootstrap (essential dependencies only)
# ----------------------------------------------------------------------------
# NOTE: Ubuntu 24.04 uses libopenmpi3t64 (t64 transition packages)
# We pin MPI versions and use --no-upgrade to prevent CUDA downgrades
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      git wget curl jq \
      software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update -y && \
    # openmpi-bin provides orted/mpirun executables required by mpi4py during quantization
    apt-get install -y --no-install-recommends --no-upgrade \
      python3.10 python3.10-venv python3.10-dev \
      python3-venv python3-dev \
      libopenmpi3t64=${MPI_VERSION_PIN} \
      openmpi-bin=${MPI_VERSION_PIN} \
      openmpi-common=${MPI_VERSION_PIN} \
      build-essential \
      libzmq3-dev && \
    apt-mark hold libopenmpi3t64 openmpi-bin openmpi-common && \
    rm -rf /var/lib/apt/lists/*

# Create virtual env (Python 3.10 via deadsnakes)
RUN python3.10 -m venv "$VENV_DIR" && \
    source "$VENV_DIR/bin/activate" && \
    python -m ensurepip --upgrade || true && \
    python -m pip install --upgrade --no-cache-dir pip setuptools wheel

# Make venv default
ENV PATH="/opt/venv/bin:${PATH}"

# ----------------------------------------------------------------------------
# PyTorch installation (TRT-LLM 1.2.0rc6 requires torch 2.9.x + CUDA 13.0)
# ----------------------------------------------------------------------------
RUN echo "Using PyTorch index: ${PYTORCH_INDEX_URL}" && \
    pip install --no-cache-dir --index-url "${PYTORCH_INDEX_URL}" \
      torch==2.9.0+cu130 \
      torchvision==0.24.0+cu130

# ----------------------------------------------------------------------------
# App Python dependencies
# ----------------------------------------------------------------------------
WORKDIR /app
COPY requirements.txt /app/requirements.txt
# Install requirements excluding torch (already installed) and mpi4py (needs MPI dev libs)
RUN grep -Ev '^(torch==|torchvision==|mpi4py==)' /app/requirements.txt > /app/requirements-fast.txt && \
    pip install --no-cache-dir -r /app/requirements-fast.txt

# Prefer system CUDA libraries (no pip CUDA runtime mix)
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# ----------------------------------------------------------------------------
# TensorRT-LLM installation (runtime wheel only)
# NOTE: Do NOT use --upgrade - it can replace torch with a different CUDA version
# ----------------------------------------------------------------------------
RUN pip install --no-cache-dir \
      --index-url https://pypi.nvidia.com \
      --extra-index-url https://pypi.org/simple \
      "${TRTLLM_PIP_SPEC}"

# ----------------------------------------------------------------------------
# Copy application code and runtime scripts
# ----------------------------------------------------------------------------
COPY src/ /app/src/
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# ----------------------------------------------------------------------------
# Production environment setup
# ----------------------------------------------------------------------------
# Configure models - these are set at build time and used at runtime
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV CHAT_MODEL=${CHAT_MODEL}
ENV TOOL_MODEL=${TOOL_MODEL}

# TRT engine repo for pulling pre-built engines from HuggingFace
ENV TRT_ENGINE_REPO=${TRT_ENGINE_REPO}

# Engine type
ENV INFERENCE_ENGINE=trt

# Default directories for runtime model and engine
ENV MODELS_DIR=/opt/models
ENV ENGINES_DIR=/opt/engines
ENV TRT_ENGINE_DIR=/opt/engines/trt-chat
RUN mkdir -p "${MODELS_DIR}" "${ENGINES_DIR}" "${TRT_ENGINE_DIR}"

# Cache directories
ENV HF_HOME=/app/.hf
ENV HUGGINGFACE_HUB_CACHE=/app/.hf/hub
RUN mkdir -p /app/logs /app/.run /app/.hf

# Default environment knobs for production
ENV HF_TRANSFER=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

# SSL certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# Default server configuration
ENV HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Health check for production readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:${PORT}/healthz || exit 1

EXPOSE ${PORT}

# Default command: start the server
CMD ["/app/scripts/main.sh"]

LABEL org.opencontainers.image.title="Yap Text Inference TRT-LLM (CUDA 13.0, Py310)" \
      org.opencontainers.image.description="TensorRT-LLM inference image for pre-quantized models." \
      org.opencontainers.image.source="https://github.com/Yap-With-AI/yap-text-inference"

