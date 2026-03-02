#!/bin/bash
# EmpireBox Backup Script

INSTALL_PATH="/opt/empirebox"
BACKUP_DIR="/opt/empirebox/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="${BACKUP_DIR}/empirebox_backup_${DATE}.tar.gz"
ENV_FILE="${INSTALL_PATH}/.env"

set -euo pipefail
[ -f "${ENV_FILE}" ] && set -a && source "${ENV_FILE}" && set +a

mkdir -p "${BACKUP_DIR}"

echo "[${DATE}] Starting EmpireBox backup..."

# Dump PostgreSQL
if docker ps --filter "name=empirebox-postgres" --filter "status=running" -q | grep -q .; then
  echo "Backing up PostgreSQL..."
  docker exec empirebox-postgres pg_dumpall -U empirebox \
    > "${BACKUP_DIR}/postgres_${DATE}.sql"
fi

# Backup config and env (excluding secrets from main archive)
echo "Backing up config..."
tar -czf "${BACKUP_FILE}" \
  --exclude="${INSTALL_PATH}/.env" \
  --exclude="${INSTALL_PATH}/backups" \
  "${INSTALL_PATH}/config.json" \
  "${INSTALL_PATH}/products" \
  "${INSTALL_PATH}/openclaw" \
  2>/dev/null || true

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/empirebox_backup_*.tar.gz 2>/dev/null | tail -n +8 | xargs rm -f || true
ls -t "${BACKUP_DIR}"/postgres_*.sql 2>/dev/null | tail -n +8 | xargs rm -f || true

echo "[$(date +%Y-%m-%d_%H-%M-%S)] Backup complete: ${BACKUP_FILE}"
