#!/usr/bin/env bash
# ==============================================================================
# Opti Matrix ERP - Automated MongoDB Recovery Script
# Restores database from a compressed mongodump archive with safety confirmation.
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_archive.gz> [--drop]"
    echo "Example: $0 /var/backups/RG_erp/RG_erp_backup_20261011_010000.gz --drop"
    exit 1
fi

ARCHIVE_FILE="$1"
DROP_FLAG="${2:-}"

if [ ! -f "${ARCHIVE_FILE}" ]; then
    echo "ERROR: Backup archive file '${ARCHIVE_FILE}' does not exist!" >&2
    exit 1
fi

MONGO_URI="${MONGODB_URI:-mongodb://localhost:27017}"
DB_NAME="${MONGODB_DB_NAME:-RG_erp}"

echo "======================================================================"
echo "WARNING: You are about to restore the database '${DB_NAME}'"
echo "Source archive: ${ARCHIVE_FILE}"
if [ "${DROP_FLAG}" = "--drop" ]; then
    echo "WARNING: Existing collections in '${DB_NAME}' will be DROPPED before restore!"
fi
echo "======================================================================"

if [ -t 0 ]; then
    read -r -p "Are you sure you want to proceed with restore? (yes/NO): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        echo "Restore cancelled by user."
        exit 0
    fi
fi

EXTRA_ARGS=""
if [ "${DROP_FLAG}" = "--drop" ]; then
    EXTRA_ARGS="--drop"
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting database restore..."

if command -v mongorestore >/dev/null 2>&1; then
    mongorestore --uri="${MONGO_URI}" --archive="${ARCHIVE_FILE}" --gzip ${EXTRA_ARGS}
elif command -v docker >/dev/null 2>&1 && docker ps | grep -q RG_erp_mongodb; then
    echo "Running restore via Docker container 'RG_erp_mongodb'..."
    docker exec -i RG_erp_mongodb mongorestore --archive --gzip ${EXTRA_ARGS} < "${ARCHIVE_FILE}"
else
    echo "ERROR: Neither host mongorestore nor running RG_erp_mongodb Docker container found!" >&2
    exit 1
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Restore completed successfully."
