#!/usr/bin/env bash
# FocusFlow PostgreSQL Backup Script
# Creates a custom-format (-Fc) logical dump with SHA-256 checksum and optional retention pruning.
#
# Supports:
#   1) Docker mode (default): executes pg_dump inside PG_CONTAINER (default: focusflow-postgres)
#   2) Direct mode: used when DATABASE_URL or PGHOST is set (and --container is not explicitly passed)
#
# Usage:
#   ./scripts/backup_postgres.sh [options]
#
# Options:
#   -o, --output <file>         Output dump file path (default: <BACKUP_DIR>/<db>_<UTC_TS>.dump)
#   -d, --database <name>       PostgreSQL database name (default: $PGDATABASE or focusflow_db)
#   -U, --user <user>           PostgreSQL username (default: $PGUSER or focusflow_user)
#   -c, --container <name>      Docker container name (default: $PG_CONTAINER or focusflow-postgres)
#       --direct                Force direct pg_dump (using DATABASE_URL or PGHOST/PGPORT/PGUSER)
#       --backup-dir <dir>      Directory for auto-named dumps (default: $BACKUP_DIR or ./backups/postgres)
#       --retention-days <N>    Delete *.dump and *.dump.sha256 older than N days in BACKUP_DIR (default: 14; 0 disables)
#   -h, --help                  Show this help message

set -euo pipefail

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

PGDATABASE="${PGDATABASE:-focusflow_db}"
PGUSER="${PGUSER:-focusflow_user}"
PG_CONTAINER="${PG_CONTAINER:-focusflow-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
OUTPUT_FILE=""
FORCE_DIRECT=0
EXPLICIT_CONTAINER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -d|--database)
      PGDATABASE="$2"
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
    --backup-dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
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

if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: RETENTION_DAYS must be a non-negative integer (got '$RETENTION_DAYS')" >&2
  exit 2
fi

USE_DOCKER=1
if [[ "$FORCE_DIRECT" -eq 1 ]]; then
  USE_DOCKER=0
elif [[ "$EXPLICIT_CONTAINER" -eq 0 && ( -n "${DATABASE_URL:-}" || -n "${PGHOST:-}" ) ]]; then
  USE_DOCKER=0
elif [[ -z "$PG_CONTAINER" ]]; then
  USE_DOCKER=0
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
AUTO_NAMED=0
if [[ -z "$OUTPUT_FILE" ]]; then
  AUTO_NAMED=1
  mkdir -p "$BACKUP_DIR"
  OUTPUT_FILE="${BACKUP_DIR}/${PGDATABASE}_${TIMESTAMP}.dump"
else
  mkdir -p "$(dirname "$OUTPUT_FILE")"
fi

TMP_FILE="${OUTPUT_FILE}.tmp.$$"
CHECKSUM_FILE="${OUTPUT_FILE}.sha256"

cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

compute_sha256() {
  local target="$1"
  local dir base
  dir="$(dirname "$target")"
  base="$(basename "$target")"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$dir" && sha256sum "$base")
  elif command -v shasum >/dev/null 2>&1; then
    (cd "$dir" && shasum -a 256 "$base")
  else
    echo "ERROR: Neither sha256sum nor shasum found in PATH." >&2
    exit 1
  fi
}

now_ms() {
  python3 -c 'import time; print(int(time.time() * 1000))'
}

START_MS="$(now_ms)"

echo "[backup_postgres] Starting backup of database '${PGDATABASE}'..."
if [[ "$USE_DOCKER" -eq 1 ]]; then
  echo "[backup_postgres] Mode: docker (container=${PG_CONTAINER}, user=${PGUSER})"
  docker exec "$PG_CONTAINER" \
    pg_dump -U "$PGUSER" -d "$PGDATABASE" -Fc --no-owner --no-privileges \
    > "$TMP_FILE"
else
  echo "[backup_postgres] Mode: direct"
  if [[ -n "${DATABASE_URL:-}" ]]; then
    pg_dump "$DATABASE_URL" -Fc --no-owner --no-privileges > "$TMP_FILE"
  else
    pg_dump -U "$PGUSER" -d "$PGDATABASE" -Fc --no-owner --no-privileges > "$TMP_FILE"
  fi
fi

if [[ ! -s "$TMP_FILE" ]]; then
  echo "ERROR: Dump file is empty; backup failed." >&2
  exit 1
fi

mv "$TMP_FILE" "$OUTPUT_FILE"
compute_sha256 "$OUTPUT_FILE" > "$CHECKSUM_FILE"

END_MS="$(now_ms)"
ELAPSED_MS=$((END_MS - START_MS))
SIZE_BYTES="$(wc -c < "$OUTPUT_FILE" | tr -d ' ')"
SIZE_HUMAN="$(du -h "$OUTPUT_FILE" | awk '{print $1}')"
SHA_VALUE="$(awk '{print $1}' "$CHECKSUM_FILE")"

echo "[backup_postgres] Backup completed successfully."
echo "  Dump file  : ${OUTPUT_FILE}"
echo "  Checksum   : ${CHECKSUM_FILE} (sha256=${SHA_VALUE})"
echo "  Size       : ${SIZE_BYTES} bytes (${SIZE_HUMAN})"
echo "  Duration   : ${ELAPSED_MS} ms"

if [[ "$AUTO_NAMED" -eq 1 && "$RETENTION_DAYS" -gt 0 ]]; then
  echo "[backup_postgres] Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}..."
  find "$BACKUP_DIR" -maxdepth 1 -type f \( -name "*.dump" -o -name "*.dump.sha256" \) -mtime "+${RETENTION_DAYS}" -print -delete
fi
