#!/usr/bin/env bash
# -----------------------------------------------------------------
#  run_function_tools.sh - Run Module 09 function tool examples
#                         (basic, long-running, agent-as-tool, celery).
# -----------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if command -v clear >/dev/null 2>&1; then
  clear
else
  printf '\033[2J\033[H'
fi

PYTHON="./.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "Error: ${PYTHON} not found. Create a virtualenv first." >&2
  exit 1
fi

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
BLUE='\033[34m'
CYAN='\033[36m'
RESET='\033[0m'

separator() {
  printf "${DIM}%.0s-${RESET}" {1..72}
  echo
}

SCENARIO="${1:-all}"
PROMPT="${2:-RET-3101}"
SCENARIO_LC="$(printf '%s' "${SCENARIO}" | tr '[:upper:]' '[:lower:]')"

run_one() {
  local scenario="$1"
  local prompt="$2"
  separator
  printf "${BOLD}${CYAN} > Scenario: %s${RESET}  ${DIM}(prompt: %s)${RESET}\n" "${scenario}" "${prompt}"
  separator
  echo
  ${PYTHON} -m function_tools_agent.main --scenario "${scenario}" "${prompt}"
  echo
}

printf "\n${BOLD}${BLUE}Module 09 - Function Tools${RESET}\n\n"

case "${SCENARIO_LC}" in
  all|both|'')
    run_one "basic" "${PROMPT}"
    run_one "long-running" "Request manual approval for RET-4420 due to source-of-funds check"
    run_one "agent-as-tool" "${PROMPT}"
    run_one "celery" "${PROMPT}"
    ;;
  basic|long-running|agent-as-tool|celery)
    run_one "${SCENARIO_LC}" "${PROMPT}"
    ;;
  *)
    echo "Unknown scenario '${SCENARIO}'. Use: basic | long-running | agent-as-tool | celery | all" >&2
    exit 2
    ;;
esac

separator
printf "${BOLD}${GREEN} Done.${RESET}\n"

