#!/usr/bin/env bash
# vLLM fallback defaults.
#
# Sets fallback values for any configuration not already set.
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

