#!/usr/bin/env bash

# Server endpoint defaults shared between shell scripts.

server_init_network_defaults() {
  local default_client_host
  local default_bind_host
  local health_urls_override

  default_client_host="${HOST:-127.0.0.1}"
  default_bind_host="${BIND_HOST:-0.0.0.0}"

  export SERVER_PORT="${SERVER_PORT:-${PORT:-8000}}"
  export SERVER_HOST="${SERVER_HOST:-${default_client_host}}"
  export SERVER_BIND_HOST="${SERVER_BIND_HOST:-${default_bind_host}}"
  export SERVER_ADDR="${SERVER_ADDR:-${SERVER_HOST}:${SERVER_PORT}}"
  export SERVER_BIND_ADDR="${SERVER_BIND_ADDR:-${SERVER_BIND_HOST}:${SERVER_PORT}}"

  if [ -z "${SERVER_WS_URL:-}" ]; then
    SERVER_WS_URL="ws://${SERVER_ADDR}/ws"
  fi
  export SERVER_WS_URL

  health_urls_override="${SERVER_HEALTH_URLS_OVERRIDE:-}"
  if [ -n "${health_urls_override}" ]; then
    IFS=',' read -r -a SERVER_HEALTH_URLS <<< "${health_urls_override}"
  else
    SERVER_HEALTH_URLS=(
      "http://${SERVER_ADDR}/healthz"
      "http://${SERVER_ADDR}/health"
    )
  fi
  export SERVER_HEALTH_URLS

  # Local health URLs always use localhost - these are for startup probes
  # where we need to check the server from within the same container/host.
  # SERVER_HOST might be an external hostname that's not routable internally.
  SERVER_LOCAL_HEALTH_URLS=(
    "http://127.0.0.1:${SERVER_PORT}/healthz"
    "http://127.0.0.1:${SERVER_PORT}/health"
  )
  export SERVER_LOCAL_HEALTH_URLS
}

