#!/usr/bin/env bash

# lint:justify -- reason: configuration file sourced by security wrappers -- ticket: N/A
# shellcheck disable=SC2034

SONAR_SERVER_PORT="9010"
SONAR_DEFAULT_HOST_URL="http://127.0.0.1:${SONAR_SERVER_PORT}"
SONAR_DEFAULT_LOGIN="admin"
SONAR_DEFAULT_PASSWORD="admin"
SONAR_ADMIN_PASSWORD_FILE=".cache/security/sonarqube/admin-password"
SONAR_TOKEN_FILE=".cache/security/sonarqube/token"
SONAR_TOKEN_NAME="yap-text-inference-local"
SONAR_SCANNER_IMAGE="sonarsource/sonar-scanner-cli:11"
SONAR_SERVER_IMAGE="sonarqube:${SONARQUBE_VERSION}-community"
SONAR_SERVER_CONTAINER_NAME="yap-text-inference-sonarqube"
SONAR_SETTINGS_FILE="sonar-project.properties"
SONAR_QUALITYGATE_WAIT="true"
SONAR_QUALITYGATE_TIMEOUT="300"
SONAR_DASHBOARD_ID="yap-text-inference"
SONAR_QUALITY_GATE_NAME="Yap Text Inference"
SONAR_QUALITY_PROFILE_NAME="Yap Text Inference Python"
SONAR_PROFILE_LANGUAGES=("py")
SONAR_GATE_CONDITIONS=(
  "new_bugs:GT:0"
  "new_vulnerabilities:GT:0"
  "new_coverage:LT:80"
  "new_duplicated_lines_density:GT:4"
  "bugs:GT:0"
  "vulnerabilities:GT:0"
  "coverage:LT:80"
  "duplicated_lines_density:GT:4"
  "reliability_rating:GT:1"
  "security_rating:GT:1"
)
SONAR_LOCALHOST_URLS=("http://127.0.0.1:${SONAR_SERVER_PORT}" "http://localhost:${SONAR_SERVER_PORT}")
SONAR_REPORT_HEADER_TEMPLATE="linting/config/security/sonarqube/report-header.md"
SONAR_TODOS_HEADER_TEMPLATE="linting/config/security/sonarqube/todos-header.md"
SONAR_CONFIG_FOOTER_TEMPLATE="linting/config/security/sonarqube/config-footer.md"
SONAR_REPORT_ISSUE_SEVERITIES=(BLOCKER CRITICAL MAJOR MINOR INFO)
SONAR_REPORT_HOTSPOT_PROBABILITIES=(HIGH MEDIUM LOW)
SONAR_REPORT_PAGE_SIZE="500"
SONAR_REPORT_MESSAGE_MAX_LENGTH="150"
SONAR_SUMMARY_METRICS_INT=(
  "ncloc:Lines of Code"
  "bugs:Bugs"
  "vulnerabilities:Vulnerabilities"
  "security_hotspots:Security Hotspots"
  "code_smells:Code Smells"
)
SONAR_SUMMARY_METRICS_PERCENT=(
  "duplicated_lines_density:Duplication %"
  "coverage:Coverage %"
)
SONAR_SUMMARY_COGNITIVE_COMPLEXITY_METRIC="cognitive_complexity"
SONAR_SUMMARY_COGNITIVE_COMPLEXITY_LABEL="Cognitive Complexity"
SONAR_SUMMARY_METRICS_RATING=(
  "reliability_rating:Reliability Rating"
  "security_rating:Security Rating"
)
SONAR_GATE_CONDITION_LABELS=(
  "new_bugs:New bugs"
  "new_vulnerabilities:New vulnerabilities"
  "new_coverage:New coverage"
  "new_duplicated_lines_density:New duplicated lines %"
  "bugs:Overall bugs"
  "vulnerabilities:Overall vulnerabilities"
  "coverage:Overall coverage"
  "duplicated_lines_density:Overall duplication %"
  "reliability_rating:Reliability rating"
  "security_rating:Security rating"
)
SONAR_REPORT_PROFILE_LANGUAGES=("py")
SONAR_PROFILE_LANGUAGE_LABELS=("py:Python")
