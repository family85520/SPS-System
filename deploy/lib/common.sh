#!/bin/bash
# ============================================
# deploy/lib/common.sh — 共享工具函数
# 所有部署脚本的基础依赖
# ============================================

set -o pipefail

# ---------- 颜色与格式 ----------
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# ---------- 日志级别 ----------
LOG_LEVEL="${DEPLOY_LOG_LEVEL:-info}"  # debug|info|warn|error

_log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case "$level" in
        DEBUG) [[ "$LOG_LEVEL" == "debug" ]] || return 0 ;;
        INFO)  ;;
        WARN)  ;;
        ERROR) ;;
    esac
    case "$level" in
        DEBUG) echo -e "${CYAN}[${timestamp}] [DEBUG]${NC} $msg" ;;
        INFO)  echo -e "${BLUE}[${timestamp}] [INFO]${NC}   $msg" ;;
        WARN)  echo -e "${YELLOW}[${timestamp}] [WARN]${NC}   $msg" ;;
        ERROR) echo -e "${RED}[${timestamp}] [ERROR]${NC}  $msg" >&2 ;;
    esac
}

log_debug() { _log DEBUG "$@"; }
log_info()  { _log INFO  "$@"; }
log_warn()  { _log WARN  "$@"; }
log_error() { _log ERROR "$@"; }
log_success() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[${timestamp}] [OK]${NC}   $*"
}

log_section() {
    echo ""
    echo -e "${BOLD}${BLUE}═══ $* ═══${NC}"
    echo ""
}

# ---------- 命令检测 ----------
check_command() {
    if ! command -v "$1" &>/dev/null; then
        log_error "未找到命令: $1"
        log_error "请先安装: $1"
        return 1
    fi
    return 0
}

# ---------- 参数解析 ----------
declare -gA OPT_ARGS=()

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --*)
                local key="${1#--}"
                local value=""
                if [[ "$key" == *"="* ]]; then
                    value="${key#*=}"
                    key="${key%%=*}"
                elif [[ $# -gt 1 && "$2" != --* ]]; then
                    value="$2"
                    shift
                else
                    value="true"
                fi
                OPT_ARGS["$key"]="$value"
                ;;
            *) shift ;;
        esac
    done
}

get_opt() {
    echo "${OPT_ARGS[$1]:-}"
}

has_opt() {
    [[ -n "${OPT_ARGS[$1]+x}" ]]
}

# ---------- 应用目录自动检测 ----------
detect_app_dir() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    echo "$script_dir"
}

# ---------- 健康检查 ----------
health_check() {
    local url="${1:-http://localhost:8000/health}"
    local max_retries="${2:-10}"
    local retry_interval="${3:-3}"

    log_info "等待服务启动: $url"
    for i in $(seq 1 "$max_retries"); do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "服务健康检查通过 ($url)"
            return 0
        fi
        log_debug "等待服务启动... ($i/$max_retries)"
        sleep "$retry_interval"
    done
    log_error "服务健康检查失败 ($url)"
    return 1
}

# ---------- 文件备份 ----------
backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$file" "${file}.bak"
        log_debug "已备份: $file -> ${file}.bak"
    fi
}

# ---------- 权限设置 ----------
secure_permissions() {
    local file="$1"
    if [[ -f "$file" ]]; then
        chmod 600 "$file"
        log_debug "已设置权限 600: $file"
    fi
}
