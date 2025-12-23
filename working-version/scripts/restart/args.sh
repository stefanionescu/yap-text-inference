#!/usr/bin/env bash

# Argument parsing for scripts/restart.sh
# Sets: INSTALL_DEPS (0|1), FORCE_REBUILD (0|1), PUSH_QUANT (0|1)

restart_parse_args() {
  INSTALL_DEPS="${INSTALL_DEPS:-0}"
  FORCE_REBUILD="${FORCE_REBUILD:-0}"
  PUSH_QUANT="${PUSH_QUANT:-0}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-deps)
        INSTALL_DEPS=1
        shift
        ;;
      --no-install-deps)
        INSTALL_DEPS=0
        shift
        ;;
      --force | --rebuild)
        FORCE_REBUILD=1
        shift
        ;;
      --push-quant)
        PUSH_QUANT=1
        shift
        ;;
      --help | -h)
        return 1
        ;;
      *)
        shift
        ;;
    esac
  done

  export INSTALL_DEPS
  export FORCE_REBUILD
  export PUSH_QUANT
  return 0
}
