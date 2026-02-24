#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

export BAGAKIT_LONG_RUN_SKILL_DIR="${BAGAKIT_LONG_RUN_SKILL_DIR:-${project_root}/.codex/skills/bagakit-long-run}"
export BAGAKIT_LIVING_DOCS_SKILL_DIR="${BAGAKIT_LIVING_DOCS_SKILL_DIR:-${project_root}/.codex/skills/bagakit-living-docs}"

if [[ ! -d "$BAGAKIT_LONG_RUN_SKILL_DIR" ]]; then
  echo "error: BAGAKIT_LONG_RUN_SKILL_DIR not found: $BAGAKIT_LONG_RUN_SKILL_DIR" >&2
  exit 1
fi

if [[ ! -d "$BAGAKIT_LIVING_DOCS_SKILL_DIR" ]]; then
  echo "error: BAGAKIT_LIVING_DOCS_SKILL_DIR not found: $BAGAKIT_LIVING_DOCS_SKILL_DIR" >&2
  exit 1
fi
