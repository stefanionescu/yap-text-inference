#!/usr/bin/env bash

set -euo pipefail

# emit_summary_table_header - Print the summary table header for the configured project list.
emit_summary_table_header() {
  local header='| Metric'
  local divider='|--------'
  local project

  for project in "${PROJECTS[@]}"; do
    header="${header} | ${project}"
    divider="${divider} |---------"
  done

  echo "${header} |"
  echo "${divider} |"
}

# collect_summary_metric_keys - Build the comma-separated measure list needed for summary queries.
collect_summary_metric_keys() {
  local keys=()
  local entry
  local metric
  local joined=""

  for entry in "${SONAR_SUMMARY_METRICS_INT[@]}"; do
    metric="${entry%%:*}"
    keys+=("${metric}")
  done
  for entry in "${SONAR_SUMMARY_METRICS_PERCENT[@]}"; do
    metric="${entry%%:*}"
    keys+=("${metric}")
  done
  keys+=("${SONAR_SUMMARY_COGNITIVE_COMPLEXITY_METRIC}")
  for entry in "${SONAR_SUMMARY_METRICS_RATING[@]}"; do
    metric="${entry%%:*}"
    keys+=("${metric}")
  done

  for metric in "${keys[@]}"; do
    if [[ -z ${joined} ]]; then
      joined="${metric}"
    else
      joined="${joined},${metric}"
    fi
  done

  echo "${joined}"
}

# emit_summary_table - Print the configured summary metrics for each project.
emit_summary_table() {
  local metric_keys
  metric_keys="$(collect_summary_metric_keys)"

  declare -A measures
  local project
  local entry
  local metric
  local label
  local row
  local value

  for project in "${PROJECTS[@]}"; do
    measures["${project}"]="$(sonar_api_get "/api/measures/component?component=${project}&metricKeys=${metric_keys}")"
  done

  emit_summary_table_header

  for entry in "${SONAR_SUMMARY_METRICS_INT[@]}"; do
    metric="${entry%%:*}"
    label="${entry#*:}"
    row="| ${label}"
    for project in "${PROJECTS[@]}"; do
      value="$(extract_measure_value "${measures[${project}]}" "${metric}")"
      row="${row} | ${value}"
    done
    echo "${row} |"
  done

  for entry in "${SONAR_SUMMARY_METRICS_PERCENT[@]}"; do
    metric="${entry%%:*}"
    label="${entry#*:}"
    row="| ${label}"
    for project in "${PROJECTS[@]}"; do
      value="$(extract_measure_value "${measures[${project}]}" "${metric}")"
      if [[ ${value} != "—" ]]; then
        value="${value}%"
      fi
      row="${row} | ${value}"
    done
    echo "${row} |"
  done

  row="| ${SONAR_SUMMARY_COGNITIVE_COMPLEXITY_LABEL}"
  for project in "${PROJECTS[@]}"; do
    value="$(extract_measure_value "${measures[${project}]}" "${SONAR_SUMMARY_COGNITIVE_COMPLEXITY_METRIC}")"
    row="${row} | ${value}"
  done
  echo "${row} |"

  for entry in "${SONAR_SUMMARY_METRICS_RATING[@]}"; do
    metric="${entry%%:*}"
    label="${entry#*:}"
    row="| ${label}"
    for project in "${PROJECTS[@]}"; do
      value="$(extract_measure_value "${measures[${project}]}" "${metric}")"
      value="$(rating_letter "${value}")"
      row="${row} | ${value}"
    done
    echo "${row} |"
  done
  echo ""
}

# emit_quality_gate_status - Print the quality gate status and per-condition values.
emit_quality_gate_status() {
  echo "## Quality Gate Status"
  echo ""

  local project
  local gate
  local gate_status

  for project in "${PROJECTS[@]}"; do
    gate="$(sonar_api_get "/api/qualitygates/project_status?projectKey=${project}")"
    gate_status="$(echo "${gate}" | jq -r '.projectStatus.status // "NONE"' 2>/dev/null || echo "NONE")"

    if [[ ${gate_status} == "OK" ]]; then
      echo "### ${project}: **PASS**"
    else
      echo "### ${project}: **FAIL**"
    fi

    echo ""
    echo "| Condition | Actual | Threshold | Status |"
    echo "|-----------|--------|-----------|--------|"

    echo "${gate}" | jq -r '.projectStatus.conditions[]? | "\(.metricKey)\t\(.actualValue // "—")\t\(.errorThreshold // "—")\t\(.status // "NONE")"' 2>/dev/null |
      while IFS=$'\t' read -r c_metric c_actual c_threshold c_status; do
        local status_label="ok"
        if [[ ${c_status} == "ERROR" ]]; then
          status_label="FAIL"
        fi
        printf '| %s | %s | %s | %s |\n' \
          "$(gate_condition_label "${c_metric}")" \
          "${c_actual}" \
          "$(format_gate_threshold "${c_metric}" "${c_threshold}")" \
          "${status_label}"
      done
    echo ""
  done
}
