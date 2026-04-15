#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
SERVICE_NAME="module14a-postgres"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-6433}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-adk_sessions}"
DB_SCHEMA="${DB_SCHEMA:-adk_module14a}"

export PGPASSWORD="${DB_PASSWORD}"

usage() {
  cat <<'EOF'
Usage:
  ./db_persist/14A/manage_postgres.sh <command>

Commands:
  up             Start postgres via docker compose
  down           Stop postgres compose stack
  destroy        Stop stack and delete container + volume data
  create-db      Create database if missing
  create-schema  Create schema in DB if missing
  reset-db       Drop and recreate database, then create schema
  reset-schema   Drop and recreate schema only
  status         Show compose status
  psql           Open interactive psql shell in target DB

Environment overrides:
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA
EOF
}

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

exec_psql() {
  local database="$1"
  local sql="$2"
  compose exec -T "${SERVICE_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${database}" -c "${sql}"
}

ensure_running() {
  if ! compose ps --status running --services | rg -q "^${SERVICE_NAME}$"; then
    echo "Postgres is not running. Start it first:"
    echo "  ./db_persist/14A/manage_postgres.sh up"
    exit 1
  fi
}

cmd_up() {
  compose up -d
  echo "Waiting for PostgreSQL to become healthy..."
  compose ps
}

cmd_down() {
  compose down
}

cmd_destroy() {
  compose down -v --remove-orphans
}

cmd_create_db() {
  ensure_running
  exec_psql "postgres" "SELECT 'CREATE DATABASE ${DB_NAME}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\\gexec"
}

cmd_create_schema() {
  ensure_running
  cmd_create_db
  exec_psql "${DB_NAME}" "CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA};"
}

cmd_reset_db() {
  ensure_running
  exec_psql "postgres" "DROP DATABASE IF EXISTS ${DB_NAME};"
  exec_psql "postgres" "CREATE DATABASE ${DB_NAME};"
  exec_psql "${DB_NAME}" "CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA};"
}

cmd_reset_schema() {
  ensure_running
  cmd_create_db
  exec_psql "${DB_NAME}" "DROP SCHEMA IF EXISTS ${DB_SCHEMA} CASCADE;"
  exec_psql "${DB_NAME}" "CREATE SCHEMA ${DB_SCHEMA};"
}

cmd_status() {
  compose ps
}

cmd_psql() {
  ensure_running
  compose exec "${SERVICE_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"
}

COMMAND="${1:-}"

case "${COMMAND}" in
  up) cmd_up ;;
  down) cmd_down ;;
  destroy) cmd_destroy ;;
  create-db) cmd_create_db ;;
  create-schema) cmd_create_schema ;;
  reset-db) cmd_reset_db ;;
  reset-schema) cmd_reset_schema ;;
  status) cmd_status ;;
  psql) cmd_psql ;;
  ""|-h|--help|help) usage ;;
  *)
    echo "Unknown command: ${COMMAND}"
    echo
    usage
    exit 1
    ;;
esac
