#!/usr/bin/env bash
# collect_sonarqube_results - Generate cached markdown reports and print the local SonarQube summary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/bootstrap.sh
source "${SCRIPT_DIR}/lib/bootstrap.sh"
# shellcheck source=lib/constants.sh
source "${SCRIPT_DIR}/lib/constants.sh"
# shellcheck source=lib/api.sh
source "${SCRIPT_DIR}/lib/api.sh"
# shellcheck source=lib/gate.sh
source "${SCRIPT_DIR}/lib/gate.sh"
# shellcheck source=lib/report/common.sh
source "${SCRIPT_DIR}/lib/report/common.sh"
# shellcheck source=lib/report/summary.sh
source "${SCRIPT_DIR}/lib/report/summary.sh"
# shellcheck source=lib/report/issues.sh
source "${SCRIPT_DIR}/lib/report/issues.sh"
# shellcheck source=lib/report/hotspots.sh
source "${SCRIPT_DIR}/lib/report/hotspots.sh"
# shellcheck source=lib/report/configuration.sh
source "${SCRIPT_DIR}/lib/report/configuration.sh"

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required for SonarQube report collection" >&2
  exit 1
fi

REPORT_HEADER_TEMPLATE="$(resolve_sonar_repo_path "${SONAR_REPORT_HEADER_TEMPLATE}")"
TODOS_HEADER_TEMPLATE="$(resolve_sonar_repo_path "${SONAR_TODOS_HEADER_TEMPLATE}")"
CONFIG_FOOTER_TEMPLATE="$(resolve_sonar_repo_path "${SONAR_CONFIG_FOOTER_TEMPLATE}")"
REPORT_FILE="${SONAR_ARTIFACT_DIR}/sonar-report.md"
TODOS_FILE="${SONAR_ARTIFACT_DIR}/sonar-todos.md"

for template_path in "${REPORT_HEADER_TEMPLATE}" "${TODOS_HEADER_TEMPLATE}" "${CONFIG_FOOTER_TEMPLATE}"; do
  if [[ ! -f ${template_path} ]]; then
    echo "error: missing SonarQube report template: ${template_path}" >&2
    exit 1
  fi
done

mkdir -p "${SONAR_ARTIFACT_DIR}"

# shellcheck disable=SC2034 # lint:justify -- reason: report helpers consume the project list via sourced shell modules -- ticket: N/A
PROJECTS=("${SONAR_DASHBOARD_ID}")

{
  render_markdown_template "${REPORT_HEADER_TEMPLATE}"
  emit_summary_table
  emit_quality_gate_status
  emit_project_issues
  emit_configuration_reference "${CONFIG_FOOTER_TEMPLATE}"
} >"${REPORT_FILE}"

{
  render_markdown_template "${TODOS_HEADER_TEMPLATE}"
  emit_summary_table
  emit_quality_gate_status
  emit_todos_issues
  emit_configuration_reference "${CONFIG_FOOTER_TEMPLATE}"
} >"${TODOS_FILE}"

echo "SonarQube dashboard: ${SONAR_DASHBOARD_URL}"
echo "SonarQube report: ${REPORT_FILE}"
echo "SonarQube todos: ${TODOS_FILE}"
print_quality_gate_summary
