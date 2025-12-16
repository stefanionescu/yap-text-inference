#!/usr/bin/env bash

# Argument parsing for custom/restart.sh
# Sets: INSTALL_DEPS (0|1)

restart_parse_args() {
  INSTALL_DEPS="${INSTALL_DEPS:-0}"

  for arg in "$@"; do
    case "${arg}" in
      --install-deps)
        INSTALL_DEPS=1
        ;;
      --no-install-deps)
        INSTALL_DEPS=0
        ;;
      --help | -h)
        return 1
        ;;
      *) : ;;
    esac
  done

  export INSTALL_DEPS
  return 0
}
