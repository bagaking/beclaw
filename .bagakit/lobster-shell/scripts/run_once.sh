#!/usr/bin/env bash
set -euo pipefail

root="."
run_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      root="$2"
      shift 2
      ;;
    --run-id)
      run_id="$2"
      shift 2
      ;;
    *)
      echo "usage: run_once.sh [--root <project-root>] [--run-id <id>]" >&2
      exit 1
      ;;
  esac
done

root="$(cd "$root" && pwd)"
if [[ -z "$run_id" ]]; then
  run_id="$(date -u +"%Y%m%dT%H%M%SZ")"
fi

source "$root/.bagakit/lobster-shell/scripts/bagakit_env.sh"

runner="$root/.bagakit/long-run/ralphloop-runner.sh"
if [[ ! -f "$runner" ]]; then
  echo "error: missing long-run runner: $runner" >&2
  exit 1
fi

if [[ -z "${BAGAKIT_AGENT_CMD:-}" && -z "${BAGAKIT_AGENT_CLI:-}" ]]; then
  echo "error: BAGAKIT_AGENT_CMD (or BAGAKIT_AGENT_CLI) is required for run-once dispatch" >&2
  exit 2
fi

runtime_dir="$root/.bagakit/lobster-shell/runtime"
mkdir -p "$runtime_dir"
run_log="$runtime_dir/run-${run_id}.log"

export RALPHLOOP_ONE_SHOT=1
export RALPHLOOP_MAX_ROUNDS="${RALPHLOOP_MAX_ROUNDS:-1}"
export RALPHLOOP_MAX_RUNTIME_SECONDS="${RALPHLOOP_MAX_RUNTIME_SECONDS:-1200}"
export RALPHLOOP_MAX_INTERVAL_SECONDS="${RALPHLOOP_MAX_INTERVAL_SECONDS:-30}"
export RALPHLOOP_SLEEP_SECONDS=0
export RALPHLOOP_JSON_MODE=1
export RALPHLOOP_LOG_FILE="${RALPHLOOP_LOG_FILE:-$root/.bagakit/long-run/logs/ralphloop-runner.log}"

set +e
runner_output="$(bash "$runner" 2>&1)"
rc=$?
set -e

printf "%s\n" "$runner_output" > "$run_log"

status="completed"
if [[ "$rc" -ne 0 ]]; then
  status="failed"
fi

python3 - "$status" "$run_id" "$rc" "$run_log" <<"PY"
import json
import sys
status, run_id, rc, run_log = sys.argv[1:5]
print(json.dumps({
    "status": status,
    "run_id": run_id,
    "exit_code": int(rc),
    "run_log": run_log,
}, ensure_ascii=False))
PY

exit "$rc"
