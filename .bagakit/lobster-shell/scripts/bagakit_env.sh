#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
project_skills_root="${project_root}/.codex/skills"
home_skills_root="${BAGAKIT_HOME:-$HOME/.bagakit}/skills"
runtime_skill_paths_env="${project_root}/.bagakit/lobster-shell/runtime/skill-paths.env"

if [[ -f "${runtime_skill_paths_env}" ]]; then
  # shellcheck disable=SC1090
  source "${runtime_skill_paths_env}"
fi

resolve_skill_dir() {
  local env_key="$1"
  local skill_name="$2"
  local env_value="${!env_key:-}"
  local project_candidate="${project_skills_root}/${skill_name}"
  local home_candidate="${home_skills_root}/${skill_name}"

  if [[ -n "$env_value" ]]; then
    if [[ -d "$env_value" ]]; then
      printf "%s\n" "$env_value"
      return 0
    fi
    echo "error: ${env_key} points to missing directory: ${env_value}" >&2
    return 1
  fi

  if [[ -d "$project_candidate" ]]; then
    printf "%s\n" "$project_candidate"
    return 0
  fi
  if [[ -d "$home_candidate" ]]; then
    printf "%s\n" "$home_candidate"
    return 0
  fi

  echo "error: cannot resolve ${skill_name}; checked:" >&2
  echo "  - ${env_key}" >&2
  echo "  - ${project_candidate}" >&2
  echo "  - ${home_candidate}" >&2
  return 1
}

export BAGAKIT_LONG_RUN_SKILL_DIR="$(resolve_skill_dir BAGAKIT_LONG_RUN_SKILL_DIR bagakit-long-run)"
export BAGAKIT_LIVING_DOCS_SKILL_DIR="$(resolve_skill_dir BAGAKIT_LIVING_DOCS_SKILL_DIR bagakit-living-docs)"
