#!/bin/bash
# ============================================
# deploy/lib/db_helper.sh — 数据库管理工具
# ============================================

# 引入 common.sh（如果尚未引入）
if ! declare -f log_info &>/dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"
fi

# ---------- 解析 DATABASE_URL ----------
# 格式: postgresql+asyncpg://user:pass@host:port/dbname
# 输出设置到全局变量: DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
parse_database_url() {
    local database_url="$1"

    if [[ -z "$database_url" ]]; then
        log_error "DATABASE_URL 为空"
        return 1
    fi

    # 提取协议部分（postgresql+asyncpg:// 或 postgresql://）
    local url_body="${database_url#*://}"

    # 提取用户:密码
    local user_pass="${url_body%%@*}"
    DB_USER="${user_pass%%:*}"
    DB_PASS="${user_pass#*:}"

    # 提取 host:port/db
    local host_part="${url_body#*@}"
    DB_PORT="${host_part##*:}"
    DB_HOST="${host_part%:*}"
    # 去掉端口得到 dbname
    DB_NAME="${DB_HOST##*/}"
    DB_HOST="${DB_HOST%/*}"

    # 默认值
    DB_PORT="${DB_PORT:-5432}"
    DB_HOST="${DB_HOST:-localhost}"

    log_debug "数据库配置: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    return 0
}

# ---------- 创建数据库用户 ----------
create_database_user() {
    local user="$1"
    local password="$2"

    log_info "确保数据库用户 '$user' 存在..."

    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$user'" | grep -q 1; then
        log_debug "用户 '$user' 已存在"
    else
        sudo -u postgres psql -c "CREATE USER \"$user\" WITH PASSWORD '$password';"
        log_success "数据库用户 '$user' 已创建"
    fi
}

# ---------- 创建数据库 ----------
create_database() {
    local dbname="$1"
    local owner="$2"

    log_info "确保数据库 '$dbname' 存在..."

    if sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$dbname'" | grep -q 1; then
        log_debug "数据库 '$dbname' 已存在"
    else
        sudo -u postgres psql -c "CREATE DATABASE \"$dbname\" OWNER \"$owner\";"
        log_success "数据库 '$dbname' 已创建"
    fi
}

# ---------- 测试数据库连接 ----------
test_db_connection() {
    local database_url="$1"

    log_info "测试数据库连接..."

    # 转换 asyncpg URL 为 psql 可识别的格式
    local psql_url="${database_url/postgresql\+asyncpg:/postgresql:/}"

    if PGPASSWORD="${DB_PASS}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        log_success "数据库连接正常"
        return 0
    else
        log_error "数据库连接失败"
        log_error "请检查: DATABASE_URL 配置是否正确，PostgreSQL 是否运行中"
        return 1
    fi
}

# ---------- 执行 Alembic 迁移 ----------
run_alembic() {
    local app_dir="$1"
    local backend_dir="$app_dir/backend"

    log_info "执行 Alembic 数据库迁移..."

    if [[ ! -f "$backend_dir/alembic.ini" ]]; then
        log_error "未找到 alembic.ini，请确认在正确的目录执行"
        return 1
    fi

    cd "$backend_dir"

    # 激活虚拟环境
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    else
        log_error "未找到 venv/bin/activate"
        return 1
    fi

    # 执行升级
    alembic upgrade head

    if [[ $? -eq 0 ]]; then
        log_success "数据库迁移完成"
    else
        log_error "数据库迁移失败"
        return 1
    fi
}
