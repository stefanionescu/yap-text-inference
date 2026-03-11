#!/usr/bin/env bash

set -euo pipefail

# render_markdown_template - Render a markdown template with SonarQube placeholder values.
render_markdown_template() {
  local template_file="$1"
  local rendered

  rendered="$(cat "${template_file}")"
  rendered="${rendered//'{{SONAR_VERSION}}'/${SONARQUBE_VERSION}}"
  rendered="${rendered//'{{SONAR_QUALITY_GATE_NAME}}'/${SONAR_QUALITY_GATE_NAME}}"
  rendered="${rendered//'{{SONAR_DASHBOARD_URL}}'/${SONAR_DASHBOARD_URL}}"
  printf '%s\n' "${rendered}"
}

# rating_letter - Convert SonarQube numeric ratings into letter grades.
rating_letter() {
  case "$1" in
    1 | 1.0) echo "A" ;;
    2 | 2.0) echo "B" ;;
    3 | 3.0) echo "C" ;;
    4 | 4.0) echo "D" ;;
    5 | 5.0) echo "E" ;;
    *) echo "$1" ;;
  esac
}

# lookup_mapping_value - Look up a key:value entry from a mapping array.
lookup_mapping_value() {
  local key="$1"
  shift
  local entry
  local map_key
  local map_value

  for entry in "$@"; do
    map_key="${entry%%:*}"
    map_value="${entry#*:}"
    if [[ ${map_key} == "${key}" ]]; then
      echo "${map_value}"
      return 0
    fi
  done
  return 1
}

# gate_condition_label - Resolve a quality gate metric key to its display label.
gate_condition_label() {
  local metric_key="$1"
  lookup_mapping_value "${metric_key}" "${SONAR_GATE_CONDITION_LABELS[@]}" || echo "${metric_key}"
}

# gate_operator_symbol - Convert SonarQube operators to display symbols.
gate_operator_symbol() {
  local op="$1"
  case "${op}" in
    GT) echo ">" ;;
    LT) echo "<" ;;
    *) echo "${op}" ;;
  esac
}

# format_gate_threshold - Format quality gate thresholds for display.
format_gate_threshold() {
  local metric_key="$1"
  local threshold="$2"

  case "${metric_key}" in
    new_duplicated_lines_density | new_coverage | duplicated_lines_density | coverage)
      echo "${threshold}%"
      ;;
    reliability_rating | security_rating)
      rating_letter "${threshold}"
      ;;
    *)
      echo "${threshold}"
      ;;
  esac
}

# extract_measure_value - Extract a single metric value from SonarQube measures JSON.
extract_measure_value() {
  local measures_json="$1"
  local metric_key="$2"
  local value

  value="$(echo "${measures_json}" | jq -r --arg metric "${metric_key}" '.component.measures[]? | select(.metric == $metric) | .value // empty' | head -1)"
  if [[ -z ${value} ]]; then
    echo "—"
  else
    echo "${value}"
  fi
}

# truncate_report_message - Truncate long issue and hotspot messages.
truncate_report_message() {
  local message="$1"
  if ((${#message} <= SONAR_REPORT_MESSAGE_MAX_LENGTH)); then
    echo "${message}"
    return
  fi

  local keep_chars=$((SONAR_REPORT_MESSAGE_MAX_LENGTH - 3))
  if ((keep_chars < 0)); then
    keep_chars=0
  fi
  echo "${message:0:keep_chars}..."
}

# split_http_response_code - Extract the appended HTTP status code from a combined response.
split_http_response_code() {
  local response="$1"
  echo "${response}" | tail -1
}

# split_http_response_body - Extract the body from a combined response that ends with an HTTP code.
split_http_response_body() {
  local response="$1"
  echo "${response}" | sed '$d'
}

# profile_language_label - Resolve a Sonar language key to a human-friendly label.
profile_language_label() {
  local language="$1"
  lookup_mapping_value "${language}" "${SONAR_PROFILE_LANGUAGE_LABELS[@]}" || echo "${language}"
}
