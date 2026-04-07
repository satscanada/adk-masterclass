#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  run_banking.sh — Run the Module 07 banking overdraft pipeline
#                   from the command line (no UI required).
#
#  Usage:
#    ./run_banking.sh              # runs both CUST-1001 and CUST-2002
#    ./run_banking.sh approve      # runs only CUST-1001 (healthy → APPROVE)
#    ./run_banking.sh deny         # runs only CUST-2002 (weaker  → DENY)
#    ./run_banking.sh CUST-1001    # runs a specific customer ID
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="./.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "Error: ${PYTHON} not found. Create a virtualenv first." >&2
  exit 1
fi

# ── Helpers ──────────────────────────────────────────────────────

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
RED='\033[31m'
BLUE='\033[34m'
CYAN='\033[36m'
RESET='\033[0m'

separator() {
  printf "${DIM}%.0s─${RESET}" {1..72}
  echo
}

run_customer() {
  local cust_id="$1"
  local label="$2"

  separator
  printf "${BOLD}${CYAN} ▶ %s${RESET}  ${DIM}(%s)${RESET}\n" "${label}" "${cust_id}"
  separator
  echo

  ${PYTHON} -m multi_agent_banking.main "${cust_id}"

  echo
  echo
}

# ── Parse argument ───────────────────────────────────────────────

MODE="${1:-both}"
# Lowercase without ${var,,} — macOS ships Bash 3.2, which does not support that.
MODE_LC=$(printf '%s' "${MODE}" | tr '[:upper:]' '[:lower:]')

case "${MODE_LC}" in
  approve|healthy|cust-1001)
    printf "\n${BOLD}${GREEN}Banking Pipeline — APPROVE scenario${RESET}\n\n"
    run_customer "CUST-1001" "Acme Corp — healthy profile (expected: APPROVE)"
    ;;

  deny|weak*|cust-2002)
    printf "\n${BOLD}${RED}Banking Pipeline — DENY scenario${RESET}\n\n"
    run_customer "CUST-2002" "Sunrise Bakery — weaker profile (expected: DENY)"
    ;;

  both|all|'')
    printf "\n${BOLD}${BLUE}Banking Pipeline — running both scenarios${RESET}\n\n"
    run_customer "CUST-1001" "Acme Corp — healthy profile (expected: APPROVE)"
    run_customer "CUST-2002" "Sunrise Bakery — weaker profile (expected: DENY)"
    ;;

  *)
    # Treat anything else as a raw customer ID
    printf "\n${BOLD}${BLUE}Banking Pipeline — custom customer${RESET}\n\n"
    run_customer "${1}" "Custom customer ID: ${1}"
    ;;
esac

separator
printf "${BOLD}${GREEN} ✓ Done.${RESET}\n"
