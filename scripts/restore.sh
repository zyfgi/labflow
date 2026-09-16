#!/usr/bin/env bash
# LabFlow restore: expects files produced by backup.sh
# Usage: ./scripts/restore.sh <db_dump.sql> [storage.tar.gz]
set -euo pipefail

DB_DUMP="${1:?usage: restore.sh <db_dump.sql> [storage.tar.gz]}"
STORAGE_TAR="${2:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[restore] restoring PostgreSQL from ${DB_DUMP} ..."
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T postgres \
  psql -U "${POSTGRES_USER:-labflow}" "${POSTGRES_DB:-labflow}" < "${DB_DUMP}"

if [ -n "${STORAGE_TAR}" ]; then
  echo "[restore] restoring storage/ from ${STORAGE_TAR} ..."
  tar -xzf "${STORAGE_TAR}" -C "${ROOT_DIR}"
fi

echo "[restore] done."
