#!/usr/bin/env bash
# FocusFlow PostgreSQL Restore Script
# Verifies SHA-256 checksum, enforces safety guard against overwriting existing databases,
# restores via pg_restore (--no-owner --no-privileges --exit-on-error), and prints integrity counts.
#
# Usage:
#   ./scripts/restore_postgres.sh -f <dump_file> -d <target_db> [options]
#
# Options:
#   -f, --file <path>           Path to .dump file (required)
#   -d, --database <name>       Target PostgreSQL database name (required)
#   -U, --user <user>           PostgreSQL username (default: $PGUSER or focusflow_user)
#   -c, --container <name>      Docker container name (default: $PG_CONTAINER or focusflow-postgres)
#       --direct                Force direct pg_restore/psql (using DATABASE_URL or PGHOST/PGPORT/PGUSER)
#       --checksum <path>       Checksum file path (default: <dump_file>.sha256)
#       --confirm-target        Required if the target database already exists
#       --clean                 Pass --clean --if-exists to pg_restore when restoring into a populated DB
#   -h, --help                  Show this help message

set -euo pipefail

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

DUMP_FILE=""
TARGET_DB=""
PGUSER="${PGUSER:-focusflow_user}"
PG_CONTAINER="${PG_CONTAINER:-focusflow-postgres}"
CHECKSUM_FILE=""
CONFIRM_TARGET=0
CLEAN_RESTORE=0
FORCE_DIRECT=0
EXPLICIT_CONTAINER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      DUMP_FILE="$2"
      shift 2
      ;;
    -d|--database)
      TARGET_DB="$2"
      shift 2
      ;;
    -U|--user)
      PGUSER="$2"
      shift 2
      ;;
    -c|--container)
      PG_CONTAINER="$2"
      EXPLICIT_CONTAINER=1
      shift 2
      ;;
    --direct)
      FORCE_DIRECT=1
      shift
      ;;
    --checksum)
      CHECKSUM_FILE="$2"
      shift 2
      ;;
    --confirm-target)
      CONFIRM_TARGET=1
      shift
      ;;
    --clean)
      CLEAN_RESTORE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$DUMP_FILE" || -z "$TARGET_DB" ]]; then
  echo "ERROR: Both --file and --database are required." >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "ERROR: Dump file not found: ${DUMP_FILE}" >&2
  exit 1
fi

if [[ -z "$CHECKSUM_FILE" ]]; then
  CHECKSUM_FILE="${DUMP_FILE}.sha256"
fi

if [[ ! -f "$CHECKSUM_FILE" ]]; then
  echo "ERROR: SHA-256 checksum file not found: ${CHECKSUM_FILE}" >&2
  echo "Refusing to restore an unverified dump." >&2
  exit 1
fi

verify_sha256() {
  local dump="$1"
  local sumfile="$2"
  local expected actual
  expected="$(awk '{print $1}' "$sumfile" | head -n 1)"
  if [[ -z "$expected" ]]; then
    echo "ERROR: Empty checksum file: ${sumfile}" >&2
    exit 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$dump" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$dump" | awk '{print $1}')"
  else
    echo "ERROR: Neither sha256sum nor shasum found in PATH." >&2
    exit 1
  fi
  if [[ "$expected" != "$actual" ]]; then
    echo "ERROR: SHA-256 checksum mismatch!" >&2
    echo "  Expected: ${expected}" >&2
    echo "  Actual  : ${actual}" >&2
    exit 1
  fi
  echo "[restore_postgres] SHA-256 verified OK (${actual})."
}

USE_DOCKER=1
if [[ "$FORCE_DIRECT" -eq 1 ]]; then
  USE_DOCKER=0
elif [[ "$EXPLICIT_CONTAINER" -eq 0 && ( -n "${DATABASE_URL:-}" || -n "${PGHOST:-}" ) ]]; then
  USE_DOCKER=0
elif [[ -z "$PG_CONTAINER" ]]; then
  USE_DOCKER=0
fi

run_psql() {
  local db="$1"
  shift
  if [[ "$USE_DOCKER" -eq 1 ]]; then
    docker exec -i "$PG_CONTAINER" psql -U "$PGUSER" -d "$db" "$@"
  else
    psql -U "$PGUSER" -d "$db" "$@"
  fi
}

now_ms() {
  python3 -c 'import time; print(int(time.time() * 1000))'
}

# 1. Verify checksum before touching PostgreSQL
verify_sha256 "$DUMP_FILE" "$CHECKSUM_FILE"

# 2. Check whether target database already exists
DB_EXISTS="$(run_psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}';" | tr -d '[:space:]')"

if [[ "$DB_EXISTS" == "1" ]]; then
  if [[ "$CONFIRM_TARGET" -ne 1 ]]; then
    echo "ERROR: Target database '${TARGET_DB}' already exists." >&2
    echo "Refusing to restore into an existing database without --confirm-target." >&2
    exit 1
  fi
  echo "[restore_postgres] Target database '${TARGET_DB}' exists and --confirm-target was supplied."
else
  echo "[restore_postgres] Target database '${TARGET_DB}' does not exist; creating..."
  run_psql postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${TARGET_DB}\";"
fi

# 3. Restore via pg_restore
PG_RESTORE_ARGS=(--no-owner --no-privileges --exit-on-error)
if [[ "$CLEAN_RESTORE" -eq 1 ]]; then
  PG_RESTORE_ARGS+=(--clean --if-exists)
fi

START_MS="$(now_ms)"
echo "[restore_postgres] Restoring '${DUMP_FILE}' into '${TARGET_DB}'..."
if [[ "$USE_DOCKER" -eq 1 ]]; then
  docker exec -i "$PG_CONTAINER" \
    pg_restore -U "$PGUSER" -d "$TARGET_DB" "${PG_RESTORE_ARGS[@]}" \
    < "$DUMP_FILE"
else
  pg_restore -U "$PGUSER" -d "$TARGET_DB" "${PG_RESTORE_ARGS[@]}" "$DUMP_FILE"
fi
END_MS="$(now_ms)"
ELAPSED_MS=$((END_MS - START_MS))

# 4. Integrity verification summary
TABLE_COUNT="$(run_psql "$TARGET_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d '[:space:]')"
TRIGGER_COUNT="$(run_psql "$TARGET_DB" -tAc "SELECT count(*) FROM information_schema.triggers WHERE trigger_schema = 'public' AND event_manipulation = 'UPDATE' AND action_timing = 'BEFORE';" | tr -d '[:space:]')"
ALEMBIC_VER="$(run_psql "$TARGET_DB" -tAc "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d '[:space:]' || echo "N/A")"
EXTENSIONS="$(run_psql "$TARGET_DB" -tAc "SELECT string_agg(extname || ':' || extversion, ', ' ORDER BY extname) FROM pg_extension;" | tr -d '\r')"

echo "[restore_postgres] Restore completed successfully."
echo "  Target DB              : ${TARGET_DB}"
echo "  Restore duration (RTO) : ${ELAPSED_MS} ms"
echo "  Public base tables     : ${TABLE_COUNT}"
echo "  BEFORE UPDATE triggers : ${TRIGGER_COUNT}"
echo "  Alembic version        : ${ALEMBIC_VER}"
echo "  Extensions             : ${EXTENSIONS}"
