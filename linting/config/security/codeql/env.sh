#!/usr/bin/env bash

# lint:justify -- reason: configuration file sourced by security wrappers -- ticket: N/A
# shellcheck disable=SC2034

CODEQL_TOOL_NAME="codeql"
CODEQL_RELEASE_BASE_URL="https://github.com/github/codeql-cli-binaries/releases/download"
CODEQL_ARCHIVE_DARWIN="codeql-osx64.zip"
CODEQL_ARCHIVE_LINUX="codeql-linux64.zip"
CODEQL_INSTALL_SUBDIR="codeql"
CODEQL_CONFIG_FILE="linting/config/security/codeql/queries.yml"
CODEQL_RESULTS_DIR="linting/.tools/codeql/results"
CODEQL_DATABASE_DIR="linting/.tools/codeql/yap-text-inference/db-python"
CODEQL_RESULT_FILE="${CODEQL_RESULTS_DIR}/yap-text-inference-python.sarif"
CODEQL_SOURCE_ROOT="."
CODEQL_TARGET_NAME="yap-text-inference"
CODEQL_LANGUAGE="python"
CODEQL_QUERY_SUITE="codeql/python-queries:codeql-suites/python-security-and-quality.qls"
