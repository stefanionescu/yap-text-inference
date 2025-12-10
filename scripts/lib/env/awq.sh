#!/usr/bin/env bash

# AWQ-related environment (HF push, repo defaults, model URLs)

apply_awq_env() {
  # Hugging Face upload controls for AWQ builds
  export HF_AWQ_PUSH=${HF_AWQ_PUSH:-0}
  export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
  export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
  export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
  export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
  export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}

  if [ "${HF_AWQ_PUSH}" = "1" ]; then
    if [ -z "${HF_TOKEN:-}" ]; then
      log_warn "HF_AWQ_PUSH=1 but HF_TOKEN is not set. Aborting."
      return 1
    fi
    if [ -z "${HF_AWQ_CHAT_REPO}" ] || [[ "${HF_AWQ_CHAT_REPO}" == your-org/* ]]; then
      log_warn "HF_AWQ_PUSH=1 requires HF_AWQ_CHAT_REPO to point at your Hugging Face repo. Aborting."
      return 1
    fi
  fi
}


