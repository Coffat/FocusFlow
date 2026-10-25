#!/usr/bin/env bash
# FocusFlow — Schema Dump Utility
# Dumps the PostgreSQL schema (as migrated by Alembic) to docs/database/schema.sql.
# Usage: ./backend/scripts/dump_schema.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_FILE="${REPO_ROOT}/docs/database/schema.sql"

POSTGRES_USER="${POSTGRES_USER:-focusflow_user}"
POSTGRES_DB="${POSTGRES_DB:-focusflow_db}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

echo "Dumping PostgreSQL schema from ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}..."

TMP_FILE="$(mktemp)"

cat << 'HEADER' > "${TMP_FILE}"
-- ============================================================================
-- FocusFlow — PostgreSQL 16 Physical Database DDL
-- GENERATED from Alembic head via backend/scripts/dump_schema.sh
-- DO NOT EDIT BY HAND. All schema changes must go through Alembic migrations.
-- ============================================================================

HEADER

if command -v pg_dump >/dev/null 2>&1; then
    pg_dump --schema-only --no-owner --no-privileges \
        -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        >> "${TMP_FILE}"
elif command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "focusflow-postgres"; then
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-focusflow_secure_password}" focusflow-postgres \
        pg_dump --schema-only --no-owner --no-privileges \
        -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        >> "${TMP_FILE}"
else
    echo "Error: Neither pg_dump nor running focusflow-postgres container found." >&2
    rm -f "${TMP_FILE}"
    exit 1
fi

mv "${TMP_FILE}" "${TARGET_FILE}"
echo "Schema dumped successfully to ${TARGET_FILE}"
