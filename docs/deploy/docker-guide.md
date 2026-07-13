# Docker 容器化部署指南

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

---

## 1. 概述

本文档提供使用 Docker 和 Docker Compose 一键部署 SPS-System（排班管理系统）的完整方案。

**优势：**
- 环境隔离，避免依赖冲突
- 一键启动，适合开发和测试环境
- 易于横向扩展

---

## 2. 项目结构

```
deploy/docker/
├── docker-compose.yml        # 编排文件（PostgreSQL + Backend + Frontend + Nginx）
├── backend/
│   ├── Dockerfile            # 后端容器镜像
│   └── .dockerignore         # 排除文件
├── frontend/
│   ├── Dockerfile            # 前端构建镜像
│   └── nginx.conf            # Nginx 容器配置
└── postgres/
    └── init.sql              # 数据库初始化脚本（可选）
```

---

## 3. 配置文件

### 3.1 后端 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.2 前端 Dockerfile（多阶段构建）

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 3.3 Nginx 配置

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 3.4 Docker Compose 编排文件

```yaml
# deploy/docker/docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: sps-postgres
    environment:
      POSTGRES_DB: scp_db
      POSTGRES_USER: scp
      POSTGRES_PASSWORD: scp2026
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U scp"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 后端服务
  backend:
    build:
      context: ../../backend
      dockerfile: ../deploy/docker/backend/Dockerfile
    container_name: sps-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://scp:scp2026@postgres:5432/scp_db
      SECRET_KEY: change-me-in-production-use-openssl-rand-hex-32
      ALLOWED_ORIGINS: http://localhost,http://localhost:80
      DEBUG: "false"
      # 自动排班配置
      AUTO_SCHEDULE_ENABLED: "true"      # 是否启用
      AUTO_SCHEDULE_TIME: "23:00"         # 触发时间
      AUTO_SCHEDULE_ORG_IDS: "1,2,3"      # 涉及组织
      AUTO_SCHEDULE_SKIP_EXISTING: "false" # 跳过已有排班
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs/backend:/app/logs
    restart: unless-stopped

  # 前端 + Nginx
  frontend:
    build:
      context: ../../frontend
      dockerfile: ../deploy/docker/frontend/Dockerfile
    container_name: sps-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
```

---

## 4. 快速启动

```bash
# 进入部署目录
cd deploy/docker

# 构建并启动所有服务
docker compose up -d --build

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务
docker compose down

# 停止并清理数据卷（谨慎使用！）
docker compose down -v
```

---

## 5. 数据库迁移

容器启动时自动执行数据库迁移（通过 `main.py` 中的 `init_db()`）。

如需手动执行：

```bash
# 进入后端容器
docker exec -it sps-backend bash

# 执行 Alembic 迁移
alembic upgrade head

# 查看当前版本
alembic current
```

---

## 6. 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | `postgresql+asyncpg://scp:scp2026@postgres:5432/scp_db` |
| `SECRET_KEY` | JWT 签名密钥 | 必须修改（使用 `openssl rand -hex 32` 生成） |
| `ALLOWED_ORIGINS` | CORS 允许的源 | `http://localhost` |
| `DEBUG` | 调试模式 | `false` |

**生产环境建议：**

```bash
# 生成安全的 SECRET_KEY
openssl rand -hex 32
```

将生成的密钥写入 `.env` 文件或 Docker Secret。

---

## 7. 生产环境加固

### 7.1 使用 Docker Secret 管理敏感信息

```yaml
# docker-compose.prod.yml 片段
services:
  backend:
    secrets:
      - secret_key
      - db_password

secrets:
  secret_key:
    file: ./secrets/secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
```

### 7.2 限制资源使用

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 7.3 启用健康检查

已在 `docker-compose.yml` 中为 PostgreSQL 配置健康检查。可为后端添加：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## 8. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 后端无法连接数据库 | DATABASE_URL 配置错误 | 检查 hostname 是否为 `postgres`（compose 服务名） |
| 前端 404 | Nginx try_files 配置错误 | 检查 `nginx.conf` 中的 `try_files` 指令 |
| CORS 错误 | ALLOWED_ORIGINS 未包含前端域名 | 添加前端访问地址到允许列表 |
| 容器启动失败 | 端口被占用 | 修改 `ports` 映射或使用 `docker compose down` 清理 |
