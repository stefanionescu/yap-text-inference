#!/usr/bin/env bash

# Shared dependency installation helpers.

deps_export_pip() {
  export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
  export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
  export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
  export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}
  export FLASHINFER_ENABLE_AOT=${FLASHINFER_ENABLE_AOT:-1}
}


