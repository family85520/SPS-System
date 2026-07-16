#!/bin/bash
# ============================================
# deploy/linux/deploy.sh — Linux 统一部署脚本
# SPS 排班管理系统部署工具
# ============================================

set -euo pipefail

# ---------- 加载共享库 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

source "$DEPLOY_LIB_DIR/common.sh"
source "$DEPLOY_LIB_DIR/db_helper.sh"
source "$DEPLOY_LIB_DIR/nginx_helper.sh"
source "$DEPLOY_LIB_DIR/systemd_helper.sh"

# ---------- 参数解析 ----------
parse_args "$@"

APP_DIR="$(get_opt app-dir)"
DOMAIN="$(get_opt domain)"
SKIP_NGINX="$(has_opt no-nginx && echo true || echo false)"
SKIP_SYSTEMD="$(has_opt no-systemd && echo true || echo false)"
FORCE="$(has_opt force && echo true || echo false)"
DRY_RUN="$(has_opt dry-run && echo true || echo false)"
VERBOSE="$(has_opt verbose && echo true || echo false)"
SKIP_HEALTHCHECK="$(has_opt skip-healthcheck && echo true || echo false)"

# 设置日志级别
[[ "$VERBOSE" == "true" ]] && export DEPLOY_LOG_LEVEL=debug

# 检测应用目录
if [[ -z "$APP_DIR" ]]; then
    APP_DIR="$(detect_app_dir)"
fi

MODE="$(get_opt mode)"

# ---------- 辅助函数 ----------
require_env_file() {
    if [[ ! -f "$APP_DIR/backend/.env" ]]; then
        log_error "未找到 backend/.env 文件"
        log_error "请先运行: ./deploy.sh setup-env"
        exit 1
    fi
    source "$APP_DIR/backend/.env"
}

require_postgres() {
    if ! check_command psql; then
        log_error "未找到 psql 命令，请先安装 PostgreSQL 客户端"
        log_error "sudo apt install postgresql-client"
        exit 1
    fi
}

require_node() {
    if ! check_command node; then
        log_error "未找到 node 命令，请先安装 Node.js 20.x LTS"
        log_error "参考: https://nodejs.org/"
        exit 1
    fi
}

require_python312() {
    if ! check_command python3; then
        log_error "未找到 python3 命令"
        exit 1
    fi

    local py_version
    py_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )[\d.]+')
    local major minor
    major=$(echo "$py_version" | cut -d. -f1)
    minor=$(echo "$py_version" | cut -d. -f2)

    if [[ "$major" -ne 3 || "$minor" -lt 12 ]]; then
        log_error "需要 Python 3.12+，当前版本: $py_version"
        log_error "请安装 Python 3.12: sudo apt install python3.12 python3.12-venv"
        exit 1
    fi
    log_debug "Python 版本检查通过: $py_version"
}

execute_or_dry_run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] $*"
    else
        eval "$@"
    fi
}

# ---------- 命令实现 ----------

cmd_install() {
    log_section "安装系统依赖和开发环境"

    # 检测包管理器
    if check_command apt; then
        log_info "检测到 apt 包管理器..."
        execute_or_dry_run "sudo apt update"
        execute_or_dry_run "sudo apt install -y python3 python3.12 python3.12-venv python3.12-dev postgresql-client nodejs npm curl"
    elif check_command yum; then
        log_info "检测到 yum 包管理器..."
        execute_or_dry_run "sudo yum install -y python3 python3-devel postgresql nodejs curl"
    elif check_command dnf; then
        log_info "检测到 dnf 包管理器..."
        execute_or_dry_run "sudo dnf install -y python3 python3-devel postgresql nodejs curl"
    else
        log_error "不支持的包管理器，请手动安装: python3.12, nodejs, postgresql-client"
        exit 1
    fi

    # Python 虚拟环境
    log_info "配置 Python 虚拟环境..."
    require_python312
    if [[ ! -d "$APP_DIR/backend/venv" ]]; then
        execute_or_dry_run "cd '$APP_DIR/backend' && python3 -m venv venv"
        log_success "Python 虚拟环境已创建"
    else
        log_debug "虚拟环境已存在，跳过"
    fi

    # 安装 Python 依赖
    execute_or_dry_run "cd '$APP_DIR/backend' && source venv/bin/activate && pip install -r requirements.txt"
    log_success "Python 依赖安装完成"

    # 前端依赖
    log_info "安装前端依赖..."
    require_node
    if [[ ! -d "$APP_DIR/frontend/node_modules" ]]; then
        execute_or_dry_run "cd '$APP_DIR/frontend' && npm install"
        log_success "前端依赖安装完成"
    else
        log_debug "node_modules 已存在，跳过"
    fi

    log_success "安装完成！"
}

cmd_setup_db() {
    log_section "配置数据库"
    require_env_file
    require_postgres

    parse_database_url "$DATABASE_URL"
    create_database_user "$DB_USER" "$DB_PASS"
    create_database "$DB_NAME" "$DB_USER"
    run_alembic "$APP_DIR"
    test_db_connection "$DATABASE_URL"

    log_success "数据库配置完成！"
}

cmd_setup_env() {
    log_section "生成环境配置"

    local env_file="$APP_DIR/backend/.env"

    if [[ -f "$env_file" && "$FORCE" != "true" ]]; then
        log_warn "backend/.env 已存在"
        read -p "是否覆盖？(y/N) " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "取消"
            exit 0
        fi
    fi

    # 生成 SECRET_KEY
    local secret_key
    secret_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

    # 交互式输入
    log_info "请按提示输入配置信息（括号内为默认值）"

    read -p "数据库名称 [scp_db]: " input
    DB_NAME="${input:-scp_db}"

    read -p "数据库用户 [scp]: " input
    DB_USER="${input:-scp}"

    read -s -p "数据库密码 [scp2026]: " input
    echo ""
    DB_PASS="${input:-scp2026}"

    read -p "SECRET_KEY [$secret_key]: " input
    INPUT_SECRET_KEY="${input:-$secret_key}"

    read -p "允许的来源 (CORS,逗号分隔) [http://localhost:5173]: " input
    ALLOWED_ORIGINS="${input:-http://localhost:5173}"

    # 写入 .env
    cat > "$env_file" << EOF
# 数据库配置
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# JWT配置
SECRET_KEY=${INPUT_SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALGORITHM=HS256

# 应用配置
APP_NAME=排班管理系统
APP_VERSION=1.0.0
DEBUG=false

# 跨域配置
ALLOWED_ORIGINS=${ALLOWED_ORIGINS}

# 系统默认配置
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
EOF

    secure_permissions "$env_file"

    # 确保 .gitignore 包含 .env
    if ! grep -q '^\.env$' "$APP_DIR/.gitignore" 2>/dev/null; then
        echo -e "\n# Environment\n.env\n.env.*" >> "$APP_DIR/.gitignore"
        log_debug "已更新 .gitignore"
    fi

    log_success "环境配置已生成: $env_file"
}

cmd_build() {
    log_section "构建项目"
    require_env_file

    # 前端构建
    log_info "构建前端..."
    require_node
    execute_or_dry_run "cd '$APP_DIR/frontend' && npm run build"
    if [[ -d "$APP_DIR/frontend/dist" ]]; then
        log_success "前端构建完成 (dist/)"
    else
        log_error "前端构建失败: dist/ 目录不存在"
        exit 1
    fi

    # 后端依赖更新
    log_info "确保后端依赖最新..."
    execute_or_dry_run "cd '$APP_DIR/backend' && source venv/bin/activate && pip install -r requirements.txt"

    log_success "构建完成！"
}

cmd_deploy() {
    log_section "完整部署流程"

    # 1. 安装
    cmd_install

    # 2. 环境配置
    if [[ ! -f "$APP_DIR/backend/.env" ]]; then
        cmd_setup_env
    fi

    # 3. 数据库
    cmd_setup_db

    # 4. 构建
    cmd_build

    # 5. Nginx 配置
    if [[ "$SKIP_NGINX" != "true" ]]; then
        log_info "配置 Nginx..."
        DOMAIN="${DOMAIN:-localhost}"
        generate_nginx_config "$APP_DIR" "$DOMAIN"
        enable_nginx_site
    else
        log_info "跳过 Nginx 配置 (--no-nginx)"
    fi

    # 6. systemd 配置
    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        log_info "配置 systemd 服务..."
        generate_systemd_unit "$APP_DIR" 4
        enable_service
        restart_service
    else
        log_info "跳过 systemd 配置 (--no-systemd)"
    fi

    # 7. 健康检查
    if [[ "$SKIP_HEALTHCHECK" != "true" ]]; then
        health_check "http://localhost:8000/health"
    fi

    log_section "部署完成！"
    log_info "访问地址: http://${DOMAIN:-localhost}"
    log_info "管理后台: http://${DOMAIN:-localhost}/admin"
}

cmd_start() {
    log_section "启动服务"
    require_env_file

    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        enable_service
        restart_service
        if [[ "$SKIP_HEALTHCHECK" != "true" ]]; then
            health_check
        fi
    else
        log_info "手动启动后端:"
        log_info "  cd $APP_DIR/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
    fi
}

cmd_stop() {
    log_section "停止服务"
    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        stop_service
    else
        log_info "请手动停止后端进程"
    fi
}

cmd_restart() {
    log_section "重启服务"
    require_env_file

    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        restart_service
        if [[ "$SKIP_HEALTHCHECK" != "true" ]]; then
            sleep 5  # 等待服务完全停止
            health_check
        fi
    fi
}

cmd_status() {
    log_section "服务状态"
    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        get_service_status
    else
        log_info "未使用 systemd，请手动检查"
    fi

    # HTTP 健康检查
    if [[ "$SKIP_HEALTHCHECK" != "true" ]]; then
        echo ""
        health_check "http://localhost:8000/health" || true
    fi
}

cmd_rollback() {
    log_section "回滚到上一版本"

    local env_bak="$APP_DIR/backend/.env.bak"
    if [[ ! -f "$env_bak" ]]; then
        log_error "没有可用的备份 (.env.bak 不存在)"
        exit 1
    fi

    log_warn "即将回滚 backend/.env 到备份版本"
    cp "$env_bak" "$APP_DIR/backend/.env"
    secure_permissions "$APP_DIR/backend/.env"

    if [[ "$SKIP_SYSTEMD" != "true" ]]; then
        restart_service
        if [[ "$SKIP_HEALTHCHECK" != "true" ]]; then
            health_check
        fi
    fi

    log_success "回滚完成！"
}

cmd_backup() {
    log_section "数据库备份"
    require_env_file
    require_postgres

    parse_database_url "$DATABASE_URL"

    local backup_dir="$APP_DIR/backups"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/db_${timestamp}.sql"

    mkdir -p "$backup_dir"

    log_info "开始备份数据库 '$DB_NAME'..."
    PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F p -f "$backup_file"

    if [[ -f "$backup_file" ]]; then
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "备份完成: $backup_file ($size)"

        # 清理 30 天前的备份
        find "$backup_dir" -name "db_*.sql" -mtime +30 -delete 2>/dev/null || true
        log_debug "已清理 30 天前的备份文件"
    else
        log_error "备份失败"
        exit 1
    fi
}

cmd_clean() {
    log_section "清理构建产物"

    log_info "清理前端构建产物..."
    rm -rf "$APP_DIR/frontend/dist"
    rm -rf "$APP_DIR/frontend/node_modules"

    log_info "清理 Python 缓存..."
    find "$APP_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

    log_success "清理完成"
}

cmd_help() {
    cat << HELP_EOF
${BOLD}SPS 排班管理系统 — Linux 部署脚本${NC}

${BOLD}用法:${NC}
  ./deploy.sh <mode> [options]

${BOLD}Modes:${NC}
  install      安装系统依赖 + Python虚拟环境 + 前后端依赖
  setup-db     创建数据库和用户（从 .env 读取配置）
  setup-env    交互式生成 .env 配置文件
  build        前端 npm build + 后端 pip install
  deploy       完整部署流程（install → setup-env → setup-db → build → nginx → systemd）
  start        启动后端服务（systemd）
  stop         停止后端服务
  restart      重启后端服务
  status       查看服务运行状态 + 健康检查
  rollback     回滚到上一版本（恢复 .env.bak）
  backup       执行数据库备份（pg_dump）
  clean        清理构建产物
  help         显示此帮助信息

${BOLD}Options:${NC}
  --app-dir <path>      应用根目录（默认: 脚本所在目录的父目录）
  --domain <host>       域名（用于 Nginx server_name）
  --no-nginx            跳过 Nginx 配置
  --no-systemd          跳过 systemd 配置
  --force               强制覆盖已有配置
  --dry-run             仅显示将要执行的命令
  --verbose             详细日志输出
  --skip-healthcheck    跳过健康检查（CI/CD 场景）

${BOLD}示例:${NC}
  ./deploy.sh setup-env                          # 交互式生成 .env
  ./deploy.sh setup-db                           # 初始化数据库
  ./deploy.sh build                              # 仅构建
  ./deploy.sh deploy --domain example.com        # 完整部署
  ./deploy.sh status                             # 查看状态
  ./deploy.sh rollback                           # 回滚
  ./deploy.sh backup                             # 备份数据库
  ./deploy.sh deploy --dry-run --verbose         # 预览执行计划

${BOLD}环境要求:${NC}
  - Python 3.12+
  - PostgreSQL 15+
  - Node.js 20.x LTS
  - Nginx (可选，用于反向代理)
  - systemd (Linux 生产环境必需)

HELP_EOF
}

# ---------- 主入口 ----------
main() {
    if [[ -z "$MODE" ]]; then
        cmd_help
        exit 0
    fi

    log_debug "应用目录: $APP_DIR"
    log_debug "模式: $MODE"
    log_debug "域名: ${DOMAIN:-未指定}"
    log_debug "Dry-run: $DRY_RUN"

    case "$MODE" in
        install)      cmd_install ;;
        setup-db)     cmd_setup_db ;;
        setup-env)    cmd_setup_env ;;
        build)        cmd_build ;;
        deploy)       cmd_deploy ;;
        start)        cmd_start ;;
        stop)         cmd_stop ;;
        restart)      cmd_restart ;;
        status)       cmd_status ;;
        rollback)     cmd_rollback ;;
        backup)       cmd_backup ;;
        clean)        cmd_clean ;;
        help|--help|-h) cmd_help ;;
        *)
            log_error "未知模式: $MODE"
            cmd_help
            exit 1
            ;;
    esac
}

main
