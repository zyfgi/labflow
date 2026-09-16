#!/usr/bin/env bash
# LabFlow backup: PostgreSQL dump + uploaded files.
# Usage: ./scripts/backup.sh [output_dir]
set -euo pipefail

OUT_DIR="${1:-./backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${OUT_DIR}"

echo "[backup] dumping PostgreSQL..."
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-labflow}" "${POSTGRES_DB:-labflow}" \
  > "${OUT_DIR}/labflow_db_${STAMP}.sql"

echo "[backup] archiving storage/ ..."
tar -czf "${OUT_DIR}/labflow_storage_${STAMP}.tar.gz" -C "${ROOT_DIR}" storage

echo "[backup] done:"
ls -lh "${OUT_DIR}" | tail -2
