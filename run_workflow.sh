#!/usr/bin/env bash
# -----------------------------------------------------------------
#  run_workflow.sh - Run Module 08 workflow-agent scenarios for
#                    retail deposit operations (no API/UI needed).
#
#  Usage:
#    ./run_workflow.sh                          # all scenarios for RET-3101
#    ./run_workflow.sh composition strong       # composition for RET-3101
#    ./run_workflow.sh parallel weak            # parallel for RET-4420
#    ./run_workflow.sh loop RET-4420            # loop for explicit ID
# -----------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Clear terminal for a clean audit + response view (best-effort).
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

resolve_customer() {
  local raw="$1"
  local key
  key=$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]')
  case "${key}" in
    strong|healthy|ret-3101) echo "RET-3101" ;;
    weak|risk|ret-4420|week) echo "RET-4420" ;; # week: common typo for weak
    *) echo "${raw}" ;;
  esac
}

run_one() {
  local scenario="$1"
  local customer="$2"
  separator
  printf "${BOLD}${CYAN} > Scenario: %s${RESET}  ${DIM}(customer: %s)${RESET}\n" "${scenario}" "${customer}"
  separator
  echo
  ${PYTHON} -m workflow_agent.main "${customer}" --scenario "${scenario}"
  echo
}

SCENARIO="${1:-all}"
CUSTOMER_RAW="${2:-RET-3101}"
CUSTOMER_ID="$(resolve_customer "${CUSTOMER_RAW}")"
SCENARIO_LC="$(printf '%s' "${SCENARIO}" | tr '[:upper:]' '[:lower:]')"

printf "\n${BOLD}${BLUE}Workflow Agents - Retail Deposit Platform${RESET}\n\n"

case "${SCENARIO_LC}" in
  all|both|'')
    run_one "loop" "${CUSTOMER_ID}"
    run_one "parallel" "${CUSTOMER_ID}"
    run_one "composition" "${CUSTOMER_ID}"
    ;;
  loop|parallel|composition)
    run_one "${SCENARIO_LC}" "${CUSTOMER_ID}"
    ;;
  *)
    echo "Unknown scenario '${SCENARIO}'. Use: loop | parallel | composition | all" >&2
    exit 2
    ;;
esac

separator
printf "${BOLD}${GREEN} Done.${RESET}\n"

