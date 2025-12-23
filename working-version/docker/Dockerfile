# AWQ production image: CUDA 13.0.0 cudnn-devel on Ubuntu 24.04 (matches TRT-LLM 1.2.0rc5 torch 2.9.0 cu130)
FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04

# Use bash for RUN lines
SHELL ["/bin/bash", "-lc"]

# Non-interactive APT
ENV DEBIAN_FRONTEND=noninteractive

# ----------------------------------------------------------------------------
# Version pins and configurable parameters (override with --build-arg)
# ----------------------------------------------------------------------------
ARG PYTHON_VERSION=3.10
ARG MPI_VERSION_PIN=4.1.6-7ubuntu2
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
ARG TORCH_VERSION=2.9.0+cu130
ARG TORCHVISION_VERSION=0.24.0+cu130
ARG TRTLLM_PIP_SPEC=tensorrt_llm==1.2.0rc5
ARG TRTLLM_WHEEL_URL=

# ----------------------------------------------------------------------------
# System bootstrap (essential dependencies only)
# ----------------------------------------------------------------------------
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      git wget curl jq \
      software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
      python3.10 python3.10-venv python3.10-dev \
      python3-venv python3-dev \
      build-essential && \
    # MPI runtime for TensorRT-LLM (t64 suffix on Ubuntu 24.04+, pinned to match scripts/lib/environment.sh)
    # openmpi-bin provides orted/mpirun executables required by mpi4py during quantization
    MPI_PKG="libopenmpi3"; \
    if apt-cache policy libopenmpi3t64 2>/dev/null | grep -q "Candidate:"; then \
      MPI_PKG="libopenmpi3t64"; \
    fi && \
    apt-get install -y --no-install-recommends "${MPI_PKG}=${MPI_VERSION_PIN}" "openmpi-bin=${MPI_VERSION_PIN}" "openmpi-common=${MPI_VERSION_PIN}" && \
    apt-mark hold "$MPI_PKG" openmpi-bin openmpi-common && \
    rm -rf /var/lib/apt/lists/*

## Ensure consistent python and create virtual env (Python 3.10 via deadsnakes)
ENV VENV_DIR=/opt/venv
RUN python${PYTHON_VERSION} -m venv "$VENV_DIR" && \
    source "$VENV_DIR/bin/activate" && \
    python -m ensurepip --upgrade || true && \
    python -m pip install --upgrade --no-cache-dir pip setuptools wheel

# Make venv default
ENV PATH="/opt/venv/bin:${PATH}"

# ----------------------------------------------------------------------------
# PyTorch installation (TRT-LLM 1.2.0rc5 requires torch 2.9.x + CUDA 13.0)
# ----------------------------------------------------------------------------
RUN echo "Using PyTorch index: ${PYTORCH_INDEX_URL}" && \
    pip install --no-cache-dir --index-url "${PYTORCH_INDEX_URL}" \
      torch==${TORCH_VERSION} \
      torchvision==${TORCHVISION_VERSION}

# ----------------------------------------------------------------------------
# App Python dependencies (production runtime only)
# ----------------------------------------------------------------------------
WORKDIR /app
COPY requirements.txt /app/requirements.txt
# Install runtime requirements (no MPI)
RUN pip install --no-cache-dir -r /app/requirements.txt

# Prefer system CUDA libraries (no pip CUDA runtime mix, matches @custom)
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# ----------------------------------------------------------------------------
# TensorRT-LLM installation (runtime wheel only, no repo)
# NOTE: Do NOT use --upgrade - it can replace torch with a different CUDA version
# from NVIDIA's index, causing CUDA mismatch between torch and torchvision
# ----------------------------------------------------------------------------
RUN if [[ -n "${TRTLLM_WHEEL_URL}" ]]; then \
      pip install --no-cache-dir "${TRTLLM_WHEEL_URL}"; \
    else \
      pip install --no-cache-dir \
        --index-url https://pypi.nvidia.com \
        --extra-index-url https://pypi.org/simple \
        "${TRTLLM_PIP_SPEC}"; \
    fi

# Do not install pip CUDA runtimes; rely on system CUDA from base image

# ----------------------------------------------------------------------------
# Copy server code and runtime scripts into image
# ----------------------------------------------------------------------------
COPY server/ /app/server/
COPY tests/ /app/tests/
RUN rm -f /app/tests/client.py || true
COPY scripts/lib/ /app/scripts/lib/
COPY docker/scripts/start_server.sh /usr/local/bin/start_server.sh
COPY docker/scripts/environment.sh /usr/local/bin/environment.sh
COPY docker/scripts/warmup.sh /usr/local/bin/warmup.sh
RUN chmod +x /usr/local/bin/start_server.sh /usr/local/bin/environment.sh /usr/local/bin/warmup.sh

# Ensure environment defaults are loaded in all shells
ENV BASH_ENV=/usr/local/bin/environment.sh
RUN mkdir -p /etc/profile.d && printf 'test -f /usr/local/bin/environment.sh && . /usr/local/bin/environment.sh\n' > /etc/profile.d/orpheus-env.sh

# ----------------------------------------------------------------------------
# Production environment setup
# ----------------------------------------------------------------------------
# Default directories for runtime model and engine mounting
ENV MODELS_DIR=/opt/models
ENV ENGINES_DIR=/opt/engines
RUN mkdir -p "${MODELS_DIR}" "${ENGINES_DIR}"

# Default environment knobs for production
ENV HF_TRANSFER=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1

# Default server configuration
ENV HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Health check for production readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

# Default command: start the server
CMD ["bash", "-lc", "start_server.sh"]

LABEL org.opencontainers.image.title="Yap Orpheus TTS AWQ (CUDA 13.0, Py310)" \
      org.opencontainers.image.description="Lean production image with dependencies only - models and engines loaded at runtime." \
      org.opencontainers.image.source="https://github.com/Yap-With-AI/yap-orpheus-tts-api"
