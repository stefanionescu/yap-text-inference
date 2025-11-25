#!/usr/bin/env bash

# AWQ-related environment (HF push, repo defaults, model URLs)

apply_awq_env() {
  # Hugging Face upload controls for AWQ builds
  export HF_AWQ_PUSH=${HF_AWQ_PUSH:-0}
  export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
  export HF_AWQ_TOOL_REPO=${HF_AWQ_TOOL_REPO:-"your-org/tool-awq"}
  export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
  export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
  export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
  export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}
  export HF_AWQ_COMMIT_MSG_TOOL=${HF_AWQ_COMMIT_MSG_TOOL:-}

  # Pre-quantized AWQ model URLs (alternative to local quantization)
  export AWQ_CHAT_MODEL=${AWQ_CHAT_MODEL:-}
  export AWQ_TOOL_MODEL=${AWQ_TOOL_MODEL:-}

  if [ "${HF_AWQ_PUSH}" = "1" ]; then
    if [ -z "${HF_TOKEN:-}" ]; then
      log_warn "HF_AWQ_PUSH=1 but HF_TOKEN is not set. Aborting."
      return 1
    fi
    # Check if at least one repo is set (not default)
    local chat_repo_valid=0 tool_repo_valid=0
    if [ -n "${HF_AWQ_CHAT_REPO}" ] && [[ "${HF_AWQ_CHAT_REPO}" != your-org/* ]]; then
      chat_repo_valid=1
    fi
    if [ -n "${HF_AWQ_TOOL_REPO}" ] && [[ "${HF_AWQ_TOOL_REPO}" != your-org/* ]]; then
      tool_repo_valid=1
    fi
    # Require at least one valid repo to be set
    if [ "${chat_repo_valid}" = "0" ] && [ "${tool_repo_valid}" = "0" ]; then
      log_warn "HF_AWQ_PUSH=1 requires either HF_AWQ_CHAT_REPO or HF_AWQ_TOOL_REPO (or both) to be set. Aborting."
      return 1
    fi
  fi
}


