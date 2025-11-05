#!/usr/bin/env bash

# AWQ upload controls (only used if QUANTIZATION=awq and local quant is performed)
export HF_AWQ_PUSH=${HF_AWQ_PUSH:-0}
export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
export HF_AWQ_TOOL_REPO=${HF_AWQ_TOOL_REPO:-"your-org/tool-awq"}
export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}
export HF_AWQ_COMMIT_MSG_TOOL=${HF_AWQ_COMMIT_MSG_TOOL:-}


