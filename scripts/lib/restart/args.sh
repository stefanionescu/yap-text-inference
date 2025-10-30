#!/usr/bin/env bash

# Argument parsing for scripts/restart.sh
# Requires: none (sets DEPLOY_MODE and INSTALL_DEPS)

restart_parse_args() {
  DEPLOY_MODE=""
  INSTALL_DEPS="${INSTALL_DEPS:-0}"
  for arg in "$@"; do
    case "${arg}" in
      both|chat|tool)
        if [ -z "${DEPLOY_MODE}" ]; then DEPLOY_MODE="${arg}"; fi ;;
      --install-deps)
        INSTALL_DEPS=1 ;;
      --no-install-deps)
        INSTALL_DEPS=0 ;;
      --help|-h)
        return 2 ;;
      *) : ;;
    esac
  done
  DEPLOY_MODE="${DEPLOY_MODE:-both}"
  export INSTALL_DEPS DEPLOY_MODE
  return 0
}


