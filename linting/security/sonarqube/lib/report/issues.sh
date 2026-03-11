#!/usr/bin/env bash

set -euo pipefail

# emit_project_issues - Print full issue sections and hotspot summaries per project.
emit_project_issues() {
  local project
  local severity
  local sev_count
  local page
  local fetched
  local issues_json
  local batch_count

  for project in "${PROJECTS[@]}"; do
    echo "---"
    echo ""
    echo "## ${project}"
    echo ""

    for severity in "${SONAR_REPORT_ISSUE_SEVERITIES[@]}"; do
      sev_count="$(sonar_api_get "/api/issues/search?componentKeys=${project}&severities=${severity}&ps=1" | jq -r '.total // 0' 2>/dev/null || echo "0")"
      if [[ ${sev_count} == "0" ]]; then
        continue
      fi

      echo "### ${severity} (${sev_count})"
      echo ""

      page=1
      fetched=0
      while [[ ${fetched} -lt ${sev_count} ]]; do
        issues_json="$(sonar_api_get "/api/issues/search?componentKeys=${project}&severities=${severity}&ps=${SONAR_REPORT_PAGE_SIZE}&p=${page}&s=SEVERITY&asc=false")"
        batch_count="$(echo "${issues_json}" | jq -r '.issues | length // 0' 2>/dev/null || echo "0")"

        echo "${issues_json}" | jq -r --arg proj "${project}" '
          .issues[]? | "\(.rule // "unknown")\t\(.message // "")\t\(.component // "" | ltrimstr($proj + ":"))\t\(.line // "")"
        ' | while IFS=$'\t' read -r rule message component line; do
          local location="${component}"
          if [[ -n ${line} ]]; then
            location="${component}:${line}"
          fi
          message="$(truncate_report_message "${message}")"
          echo "- [${rule}] ${message}"
          echo "  - \`${location}\`"
        done

        fetched=$((fetched + batch_count))
        page=$((page + 1))
        if [[ ${batch_count} -eq 0 ]]; then
          break
        fi
      done
      echo ""
    done

    emit_project_hotspots "${project}"
  done
}

# emit_todos_issues - Print concise TODO sections aggregated by rule and severity.
emit_todos_issues() {
  local project
  local severity
  local sev_count
  local page
  local fetched
  local issues_json
  local batch_count
  local batch_rules
  local all_rules

  for project in "${PROJECTS[@]}"; do
    echo "---"
    echo ""
    echo "## ${project}"
    echo ""

    for severity in "${SONAR_REPORT_ISSUE_SEVERITIES[@]}"; do
      sev_count="$(sonar_api_get "/api/issues/search?componentKeys=${project}&severities=${severity}&ps=1" | jq -r '.total // 0' 2>/dev/null || echo "0")"
      if [[ ${sev_count} == "0" ]]; then
        continue
      fi

      echo "### ${severity} (${sev_count})"
      echo ""
      echo "| Rule | Count |"
      echo "|------|-------|"

      page=1
      fetched=0
      all_rules=""
      while [[ ${fetched} -lt ${sev_count} ]]; do
        issues_json="$(sonar_api_get "/api/issues/search?componentKeys=${project}&severities=${severity}&ps=${SONAR_REPORT_PAGE_SIZE}&p=${page}")"
        batch_count="$(echo "${issues_json}" | jq -r '.issues | length // 0' 2>/dev/null || echo "0")"
        batch_rules="$(echo "${issues_json}" | jq -r '.issues[]?.rule // empty' 2>/dev/null || true)"

        if [[ -n ${batch_rules} ]]; then
          if [[ -n ${all_rules} ]]; then
            all_rules="${all_rules}"$'\n'"${batch_rules}"
          else
            all_rules="${batch_rules}"
          fi
        fi

        fetched=$((fetched + batch_count))
        page=$((page + 1))
        if [[ ${batch_count} -eq 0 ]]; then
          break
        fi
      done

      if [[ -n ${all_rules} ]]; then
        echo "${all_rules}" | sort | uniq -c | sort -rn | while read -r count rule; do
          printf '| %s | %s |\n' "${rule}" "${count}"
        done
      fi
      echo ""
    done
  done
}
