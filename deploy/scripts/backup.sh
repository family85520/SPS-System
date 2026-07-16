#!/bin/bash
# ============================================
# deploy/scripts/backup.sh — 数据库备份脚本
# 可独立运行，也可通过 deploy.sh backup 调用
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$APP_DIR/backend/.env"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"; }
log_ok() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [OK]${NC} $*"; }
log_err() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $*" >&2; }

# 检查 .env
if [[ ! -f "$ENV_FILE" ]]; then
    log_err "未找到 $ENV_FILE"
    exit 1
fi
source "$ENV_FILE"

# 解析 DATABASE_URL
URL_BODY="${DATABASE_URL#*://}"
USER_PASS="${URL_BODY%%@*}"
DB_USER="${USER_PASS%%:*}"
DB_PASS="${USER_PASS#*:}"
HOST_PART="${URL_BODY#*@}"
DB_PORT="${HOST_PART##*:}"
DB_HOST="${HOST_PART%:*}"
DB_NAME="${DB_HOST##*/}"
DB_HOST="${DB_HOST%/*}"
DB_PORT="${DB_PORT:-5432}"
DB_HOST="${DB_HOST:-localhost}"

BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

log "开始备份数据库 '$DB_NAME'..."

PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F p -f "$BACKUP_FILE"

if [[ -f "$BACKUP_FILE" ]]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_ok "备份完成: $BACKUP_FILE ($SIZE)"

    # 清理 30 天前的备份
    find "$BACKUP_DIR" -name "db_*.sql" -mtime +30 -delete 2>/dev/null || true
    log "已清理 30 天前的备份文件"
else
    log_err "备份失败"
    exit 1
fi
