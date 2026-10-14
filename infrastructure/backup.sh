#!/usr/bin/env bash
# ==============================================================================
# Opti Matrix ERP - Automated MongoDB Backup Script
# Creates compressed, timestamped mongodump archives and cleans up old backups.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/RG_erp}"
MONGO_URI="${MONGODB_URI:-mongodb://localhost:27017}"
DB_NAME="${MONGODB_DB_NAME:-RG_erp}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
ARCHIVE_NAME="${DB_NAME}_backup_${TIMESTAMP}.gz"
TARGET_FILE="${BACKUP_DIR}/${ARCHIVE_NAME}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting database backup for '${DB_NAME}'..."

if command -v mongodump >/dev/null 2>&1; then
    mongodump --uri="${MONGO_URI}" --db="${DB_NAME}" --archive="${TARGET_FILE}" --gzip
elif command -v docker >/dev/null 2>&1 && docker ps | grep -q RG_erp_mongodb; then
    echo "Running backup via Docker container 'RG_erp_mongodb'..."
    docker exec RG_erp_mongodb mongodump --db="${DB_NAME}" --archive --gzip > "${TARGET_FILE}"
else
    echo "ERROR: Neither host mongodump nor running RG_erp_mongodb Docker container found!" >&2
    exit 1
fi

FILESIZE="$(du -h "${TARGET_FILE}" | cut -f1)"
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Backup successfully written to ${TARGET_FILE} (${FILESIZE})"

# Prune archives older than retention period
echo "Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}..."
find "${BACKUP_DIR}" -name "${DB_NAME}_backup_*.gz" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Backup procedure completed successfully."
