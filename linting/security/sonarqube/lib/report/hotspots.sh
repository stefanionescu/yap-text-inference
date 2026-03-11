#!/usr/bin/env bash

set -euo pipefail

# emit_project_hotspots - Print hotspot findings for a project, handling permission issues cleanly.
emit_project_hotspots() {
  local project="$1"
  local hotspot_cache
  local page=1
  local fetched=0
  local hotspot_total=0
  local response
  local http_code
  local hotspot_json
  local batch_count
  local cached_total
  local probability
  local prob_count

  hotspot_cache="$(mktemp)"

  while true; do
    response="$(sonar_api_get_with_code "/api/hotspots/search?projectKey=${project}&ps=${SONAR_REPORT_PAGE_SIZE}&p=${page}")"
    http_code="$(split_http_response_code "${response}")"
    hotspot_json="$(split_http_response_body "${response}")"

    if [[ ${http_code} == "403" ]]; then
      rm -f "${hotspot_cache}"
      echo "### Security Hotspots"
      echo ""
      echo "> Hotspot data unavailable — analysis credentials lack Browse permission."
      echo ""
      return
    fi

    if [[ ${http_code} != "200" ]]; then
      rm -f "${hotspot_cache}"
      echo "### Security Hotspots"
      echo ""
      echo "> Hotspot data unavailable — SonarQube API returned HTTP ${http_code}."
      echo ""
      return
    fi

    hotspot_total="$(echo "${hotspot_json}" | jq -r '.paging.total // 0' 2>/dev/null || echo "0")"
    batch_count="$(echo "${hotspot_json}" | jq -r '.hotspots | length // 0' 2>/dev/null || echo "0")"
    echo "${hotspot_json}" | jq -c '.hotspots[]?' >>"${hotspot_cache}"

    fetched=$((fetched + batch_count))
    if [[ ${batch_count} -eq 0 || ${fetched} -ge ${hotspot_total} ]]; then
      break
    fi
    page=$((page + 1))
  done

  cached_total="$(wc -l <"${hotspot_cache}" | tr -d '[:space:]')"
  if [[ ${cached_total} == "0" ]]; then
    rm -f "${hotspot_cache}"
    return
  fi

  echo "### Security Hotspots (${cached_total})"
  echo ""

  for probability in "${SONAR_REPORT_HOTSPOT_PROBABILITIES[@]}"; do
    prob_count="$(jq -s --arg p "${probability}" '[.[] | select(.vulnerabilityProbability == $p)] | length' "${hotspot_cache}")"
    if [[ ${prob_count} == "0" ]]; then
      continue
    fi

    echo "**${probability}** (${prob_count})"
    echo ""

    jq -s -r --arg proj "${project}" --arg p "${probability}" '
      .[] | select(.vulnerabilityProbability == $p) |
      "\(.securityCategory // "unknown")\t\(.message // "")\t\(.component // "" | ltrimstr($proj + ":"))\t\(.line // "")"
    ' "${hotspot_cache}" | while IFS=$'\t' read -r hs_category hs_message hs_component hs_line; do
      local hs_location="${hs_component}"
      if [[ -n ${hs_line} ]]; then
        hs_location="${hs_component}:${hs_line}"
      fi
      hs_message="$(truncate_report_message "${hs_message}")"
      echo "- [${hs_category}] ${hs_message}"
      echo "  - \`${hs_location}\`"
    done
    echo ""
  done

  rm -f "${hotspot_cache}"
}
