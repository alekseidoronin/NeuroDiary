#!/usr/bin/env bash
# PostgreSQL logical backup for diary-bot (Docker Compose on the same host).
# Usage:
#   chmod +x scripts/backup/pg_backup.sh
#   BACKUP_DIR=/var/backups/diary-bot ./scripts/backup/pg_backup.sh
#
# Cron example (daily 03:15), adjust paths:
#   15 3 * * * cd /home/debian/diary-bot && BACKUP_DIR=/var/backups/diary-bot ./scripts/backup/pg_backup.sh >> /var/log/diary-pg-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/pg}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
PG_CONTAINER="${PG_CONTAINER:-diary-bot-postgres-1}"
PG_USER="${PG_USER:-diary}"
PG_DB="${PG_DB:-diarybot}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/diarybot_${STAMP}.dump"

if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
  echo "Container $PG_CONTAINER not running. docker ps | grep postgres" >&2
  exit 1
fi

docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc >"$OUT"
echo "Wrote $OUT ($(wc -c <"$OUT" | tr -d ' ') bytes)"

find "$BACKUP_DIR" -name 'diarybot_*.dump' -type f -mtime "+${RETAIN_DAYS}" -delete 2>/dev/null || true
