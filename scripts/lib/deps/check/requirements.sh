#!/usr/bin/env bash
# =============================================================================
# Dependency Check - requirements.txt Validation
# =============================================================================
# requirements parsing, presence/version checks, and cleanup helpers.

# Array defaults
declare -a REQUIREMENTS_MISSING_PKGS
declare -a REQUIREMENTS_WRONG_VERSION_PKGS
REQUIREMENTS_MISSING=false
REQUIREMENTS_WRONG=false

# Check if requirements.txt packages are installed with correct versions
# Returns: 0 if all OK, 1 if some missing, 2 if some wrong version
# Also sets REQUIREMENTS_MISSING_PKGS and REQUIREMENTS_WRONG_VERSION_PKGS arrays
deps_requirements_parse_line() {
  local line="$1"
  line="${line%%#*}"
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"

  if [[ -z $line ]]; then
    return 1
  fi

  # Supports "pkg==1.2.3" and "pkg[extra]==1.2.3".
  if [[ $line =~ ^([a-zA-Z0-9_.-]+)(\[[^]]+\])?==([0-9][^[:space:]]*)$ ]]; then
    printf '%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[3]}"
    return 0
  fi

  return 1
}

deps_requirements_check() {
  local requirements_file="$1"
  local py_exe="${2:-python}"

  REQUIREMENTS_MISSING_PKGS=()
  REQUIREMENTS_WRONG_VERSION_PKGS=()
  REQUIREMENTS_MISSING=false
  REQUIREMENTS_WRONG=false
  local has_missing=false
  local has_wrong_version=false

  while IFS= read -r line || [[ -n $line ]]; do
    local parsed pkg_name required_ver
    parsed="$(deps_requirements_parse_line "$line")" || continue
    pkg_name="${parsed%%$'\t'*}"
    required_ver="${parsed#*$'\t'}"

    local pkg_normalized="${pkg_name//-/_}"
    local installed_ver
    installed_ver=$(get_pip_pkg_version "$pkg_normalized" "$py_exe")

    if [[ -z $installed_ver ]]; then
      installed_ver=$(get_pip_pkg_version "$pkg_name" "$py_exe")
    fi

    if [[ -z $installed_ver ]]; then
      REQUIREMENTS_MISSING_PKGS+=("$pkg_name==$required_ver")
      has_missing=true
      export REQUIREMENTS_MISSING=true
    elif [[ $installed_ver != "$required_ver" ]]; then
      REQUIREMENTS_WRONG_VERSION_PKGS+=("$pkg_name")
      has_wrong_version=true
      export REQUIREMENTS_WRONG=true
    fi
  done <"$requirements_file"

  if $has_missing; then
    return 1
  fi

  if $has_wrong_version; then
    return 2
  fi

  return 0
}

check_requirements_installed() {
  local requirements_file="${1:-requirements.txt}"
  local py_exe="${2:-python}"

  # Resolve path relative to ROOT_DIR if not absolute
  if [[ $requirements_file != /* ]]; then
    requirements_file="${ROOT_DIR}/${requirements_file}"
  fi

  if [[ ! -f $requirements_file ]]; then
    log_info "[deps] requirements.txt not found: $requirements_file"
    return 1
  fi

  deps_requirements_check "${requirements_file}" "${py_exe}"
}

# Uninstall packages that have wrong versions before reinstalling
uninstall_wrong_requirements_packages() {
  local py_exe="${1:-python}"

  if [[ ${#REQUIREMENTS_WRONG_VERSION_PKGS[@]} -gt 0 ]]; then
    log_info "[deps] Uninstalling wrong version packages..."
    for pkg in "${REQUIREMENTS_WRONG_VERSION_PKGS[@]}"; do
      $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    done
  fi
}
