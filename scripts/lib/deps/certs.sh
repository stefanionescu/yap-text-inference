#!/usr/bin/env bash
# =============================================================================
# Certificate Utilities
# =============================================================================
# Ensures CA certificates are installed and configured for HTTPS downloads
# from HuggingFace, PyPI, and other package sources.

ensure_ca_certificates() {
  if [ "$(uname -s)" = "Linux" ] && [ ! -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -y >/dev/null 2>&1 || true
      apt-get install -y ca-certificates >/dev/null 2>&1 || true
      update-ca-certificates >/dev/null 2>&1 || true
    elif command -v apk >/dev/null 2>&1; then
      apk add --no-cache ca-certificates >/dev/null 2>&1 || true
      update-ca-certificates >/dev/null 2>&1 || true
    elif command -v dnf >/dev/null 2>&1; then
      dnf install -y ca-certificates >/dev/null 2>&1 || true
      update-ca-trust >/dev/null 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
      yum install -y ca-certificates >/dev/null 2>&1 || true
      update-ca-trust >/dev/null 2>&1 || true
    fi
  fi
}

export_ca_bundle_env_vars() {
  if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    export REQUESTS_CA_BUNDLE=${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
    export CURL_CA_BUNDLE=${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
    export GIT_SSL_CAINFO=${GIT_SSL_CAINFO:-/etc/ssl/certs/ca-certificates.crt}
  fi
}
