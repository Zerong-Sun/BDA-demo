#!/usr/bin/env bash
# Database backup helper for the BDA Workbench.
#
# Supports both deployment modes:
#   - SQLite  (default): uses the online `.backup` API for a consistent snapshot.
#   - PostgreSQL       : uses `pg_dump` when BDA_DB_PATH is a postgresql:// URL.
#
# Backups are written to $BDA_BACKUP_DIR (default ./backups) with a timestamp,
# and old backups beyond $BDA_BACKUP_RETENTION (default 14) are pruned.
#
# Schedule via cron, e.g.:
#   0 2 * * * /app/scripts/backup_db.sh >> /var/log/bda-backup.log 2>&1
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${BDA_DB_PATH:-${REPO_ROOT}/backend/db/bda.sqlite3}"
BACKUP_DIR="${BDA_BACKUP_DIR:-${REPO_ROOT}/backups}"
RETENTION="${BDA_BACKUP_RETENTION:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"

if [[ "$DB_PATH" == postgresql://* || "$DB_PATH" == postgres://* ]]; then
  OUT="${BACKUP_DIR}/bda_${TIMESTAMP}.dump"
  echo "Backing up PostgreSQL to ${OUT}"
  pg_dump --format=custom --no-owner --dbname="$DB_PATH" --file="$OUT"
else
  OUT="${BACKUP_DIR}/bda_${TIMESTAMP}.sqlite3"
  echo "Backing up SQLite ${DB_PATH} to ${OUT}"
  sqlite3 "$DB_PATH" ".backup '${OUT}'"
fi

gzip -f "$OUT"
echo "Backup complete: ${OUT}.gz"

# Prune old backups, keeping the most recent $RETENTION files.
ls -1t "${BACKUP_DIR}"/bda_*.gz 2>/dev/null | tail -n +"$((RETENTION + 1))" | while read -r old; do
  echo "Pruning old backup: ${old}"
  rm -f "$old"
done
