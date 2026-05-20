#!/bin/bash
set -e

echo "========================================="
echo "  排班管理系统 Linux 安装脚本"
echo "========================================="

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DB_NAME="scheduling_db"
DB_USER="scheduling"
DB_PASS="Scheduling@2024"  # 请修改为强密码

# 1. 安装系统依赖
echo "[1/5] 安装系统依赖..."
sudo apt update
sudo apt install -y python3 python3-pip python3.11-venv postgresql postgresql-contrib nginx

# 2. 配置数据库
echo "[2/5] 配置数据库..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true

# 3. Python环境
echo "[3/5] 配置Python环境..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 环境变量
echo "[4/5] 写入环境配置..."
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=*
DEBUG=false
EOF

# 5. 数据库迁移
echo "[5/5] 初始化数据库..."
alembic revision --autogenerate -m "init tables"
alembic upgrade head

echo "========================================="
echo "  安装完成！"
echo "  启动命令: cd $APP_DIR && bash deploy/linux/start.sh"
echo "  默认账号: admin / admin123"
echo "========================================="
