#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$APP_DIR/backend"

# 激活虚拟环境
source venv/bin/activate

# 启动服务
echo "启动排班管理系统后端服务..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
