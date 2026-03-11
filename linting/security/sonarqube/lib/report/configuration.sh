#!/usr/bin/env bash

set -euo pipefail

# emit_quality_gate_reference - Print the configured quality gate conditions.
emit_quality_gate_reference() {
  local condition
  local metric
  local op
  local threshold

  echo "| Condition | Operator | Threshold |"
  echo "|-----------|----------|-----------|"

  for condition in "${SONAR_GATE_CONDITIONS[@]}"; do
    IFS=':' read -r metric op threshold <<<"${condition}"
    printf '| %s | %s | %s |\n' \
      "$(gate_condition_label "${metric}")" \
      "$(gate_operator_symbol "${op}")" \
      "$(format_gate_threshold "${metric}" "${threshold}")"
  done
}

# emit_quality_profiles_reference - Print the default quality profile and rule counts by language.
emit_quality_profiles_reference() {
  local language
  local profile_json
  local rules_json
  local profile_name
  local active_rules
  local total_rules

  echo "| Language | Profile | Active Rules | Total Available |"
  echo "|----------|---------|-------------|-----------------|"

  for language in "${SONAR_REPORT_PROFILE_LANGUAGES[@]}"; do
    profile_json="$(sonar_api_get "/api/qualityprofiles/search?language=${language}")"
    rules_json="$(sonar_api_get "/api/rules/search?languages=${language}&ps=1")"

    profile_name="$(echo "${profile_json}" | jq -r '(.profiles[]? | select(.isDefault == true) | .name) // (.profiles[0].name // "—")' 2>/dev/null || echo "—")"
    active_rules="$(echo "${profile_json}" | jq -r '(.profiles[]? | select(.isDefault == true) | .activeRuleCount) // (.profiles[0].activeRuleCount // "—")' 2>/dev/null || echo "—")"
    total_rules="$(echo "${rules_json}" | jq -r '.total // "—"' 2>/dev/null || echo "—")"

    if [[ ${total_rules} == "0" && ${profile_name} == "—" ]]; then
      profile_name="Sonar way"
      active_rules="0"
    fi

    printf '| %s | %s | %s | %s |\n' \
      "$(profile_language_label "${language}")" \
      "${profile_name}" \
      "${active_rules}" \
      "${total_rules}"
  done
}

# emit_configuration_reference - Print the effective quality gate/profile reference and report notes.
emit_configuration_reference() {
  local footer_template="$1"

  echo "---"
  echo ""
  echo "## Configuration Reference"
  echo ""
  echo "### Quality Gate: ${SONAR_QUALITY_GATE_NAME}"
  echo ""
  emit_quality_gate_reference
  echo ""
  echo "### Quality Profiles"
  echo ""
  emit_quality_profiles_reference
  echo ""
  render_markdown_template "${footer_template}"
}
