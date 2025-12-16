#!/usr/bin/env bash

# AWQ-related environment
# Push is controlled by --push-quant flag (sets HF_AWQ_PUSH=1)
# Validation is done early in main.sh/restart.sh via validate_push_quant_prereqs()

apply_awq_env() {
  # Note: HF push params (HF_PUSH_REPO_ID, HF_PUSH_PRIVATE) are defined in common params
  :
}


