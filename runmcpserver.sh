#!/usr/bin/env bash
# -----------------------------------------------------------------
#  runmcpserver.sh - Run Module 11 MCP server smoke checks
#                    (OpenAPI loader + mock payload tests).
#
#  Usage:
#    ./runmcpserver.sh                  # run both tests
#    ./runmcpserver.sh loader           # run only loader smoke test
#    ./runmcpserver.sh payload          # run only mock payload test
#    ./runmcpserver.sh all              # same as default
# -----------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if command -v clear >/dev/null 2>&1; then
  clear || true
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

run_one() {
  local label="$1"
  local script_path="$2"
  separator
  printf "${BOLD}${CYAN} > %s${RESET}  ${DIM}(%s)${RESET}\n" "${label}" "${script_path}"
  separator
  echo
  ${PYTHON} "${script_path}"
  echo
}

MODE="${1:-all}"
MODE_LC="$(printf '%s' "${MODE}" | tr '[:upper:]' '[:lower:]')"

printf "\n${BOLD}${BLUE}Module 11 - MCP Server Validation${RESET}\n\n"
printf "${DIM}Using repo virtualenv test runners. Current .env is left untouched.${RESET}\n\n"

case "${MODE_LC}" in
  all|both|'')
    run_one "OpenAPI loader smoke test" "tests/mcp_server_loader_smoke_test.py"
    run_one "Mock payload generation test" "tests/mcp_server_mock_payload_test.py"
    ;;
  loader|smoke)
    run_one "OpenAPI loader smoke test" "tests/mcp_server_loader_smoke_test.py"
    ;;
  payload|mock)
    run_one "Mock payload generation test" "tests/mcp_server_mock_payload_test.py"
    ;;
  *)
    echo "Unknown mode '${MODE}'. Use: loader | payload | all" >&2
    exit 2
    ;;
esac

separator
printf "${BOLD}${GREEN} Done.${RESET}\n"
