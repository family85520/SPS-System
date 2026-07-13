# Linux 部署手册

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

---

## 1. 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| OS | Ubuntu 20.04 / CentOS 8 | Ubuntu 22.04 LTS |
| Python | 3.12 | 3.12.x (latest patch) |
| PostgreSQL | 14 | 15+ |
| Nginx | 1.18 | 1.24+ |
| Node.js | 18.x | 20.x LTS |

---

## 2. 一键安装

```bash
# 克隆仓库
git clone <repo-url> /opt/sps-system
cd /opt/sps-system

# 运行安装脚本
sudo bash deploy/linux/install.sh
```

> **注意：** 安装脚本中的数据库名称、用户和密码需要修改为你自己的值。

---

## 3. 手动部署步骤

### 3.1 后端部署

```bash
# 创建应用目录
sudo mkdir -p /opt/sps-system
cd /opt/sps-system

# 克隆代码（或上传代码包）
git clone <repo-url> .

# 创建虚拟环境
python3.12 -m venv backend/venv
source backend/venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 填写数据库连接等信息
```

**`.env` 配置文件：**

```ini
DATABASE_URL=postgresql+asyncpg://scp:your_strong_password@localhost:5432/scp_db
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=http://your-domain.com
DEBUG=false
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=change_me_immediately
```

### 3.2 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 构建产物输出至 dist/ 目录
ls dist/
```

---

## 4. Nginx 配置

```nginx
# /etc/nginx/sites-available/sps-system
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/sps-system/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # 增加超时时间以支持长时间运行的自动排班任务
        proxy_read_timeout 300s;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;  # 24 小时超时
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/sps-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. systemd 服务配置

### 5.1 后端服务

```ini
# /etc/systemd/system/sps-backend.service
[Unit]
Description=SPS Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/sps-system/backend
Environment="PATH=/opt/sps-system/backend/venv/bin"
EnvironmentFile=/opt/sps-system/backend/.env
ExecStart=/opt/sps-system/backend/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.2 启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启动并设置开机自启
sudo systemctl start sps-backend
sudo systemctl enable sps-backend

# 查看状态
sudo systemctl status sps-backend

# 实时日志
sudo journalctl -u sps-backend -f
```

---

## 6. 数据库初始化

```bash
# 进入后端目录
cd /opt/sps-system/backend
source venv/bin/activate

# 数据库迁移（自动创建表 + 默认数据）
alembic upgrade head

# 验证数据库
psql -U scp -d scp_db -c "\dt"
```

---

## 7. 安全加固

### 7.1 修改默认密码

登录后立即修改 admin 密码：

```
1. 使用 admin / admin123 登录
2. 系统强制要求首次修改密码
3. 设置强密码（至少 12 位，含大小写+数字+特殊字符）
```

### 7.2 防火墙配置

```bash
# 仅开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 7.3 HTTPS（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 8. 备份策略

```bash
#!/bin/bash
# /opt/sps-system/scripts/backup.sh
BACKUP_DIR="/opt/backups/sps-system"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 数据库备份
pg_dump -U scp scp_db > $BACKUP_DIR/db_$DATE.sql

# 保留最近 30 天备份
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete

echo "Backup completed: $DATE"
```

添加 cron 任务每日备份：

```bash
crontab -e
# 每天凌晨 3 点备份
0 3 * * * /opt/sps-system/scripts/backup.sh
```

---

## 9. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 后端无法启动 | 数据库连接失败 | 检查 `.env` 中 `DATABASE_URL` |
| 403 Forbidden | 权限不足 | 检查用户角色分配 |
| 前端白屏 | 路由模式配置错误 | 确认 Nginx `try_files` 配置 |
| WebSocket 断开 | Nginx 超时 | 增加 `proxy_read_timeout` |
