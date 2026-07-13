# Windows 部署手册

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 开发团队

---

## 1. 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| OS | Windows 10 / Server 2019 | Windows 11 / Server 2022 |
| Python | 3.12 | 3.12.x (latest patch) |
| PostgreSQL | 14 | 15+ |
| Node.js | 18.x | 20.x LTS |
| NSSM (可选) | 2.24 | 最新版 |

---

## 2. 安装步骤

### 2.1 安装 PostgreSQL

1. 从 [PostgreSQL 官网](https://www.postgresql.org/download/windows/) 下载 Windows 安装包
2. 运行安装程序，设置密码（建议与开发环境一致：`scp2026`）
3. 端口保持默认 `5432`
4. 创建数据库 `scp_db`，用户 `scp`

### 2.2 安装 Python

1. 从 [python.org](https://www.python.org/downloads/) 下载 Python 3.12
2. 安装时勾选 **"Add Python to PATH"**

### 2.3 安装 Node.js

1. 从 [nodejs.org](https://nodejs.org/) 下载 LTS 版本
2. 安装后验证：`node -v` 和 `npm -v`

---

## 3. 后端部署

```powershell
# 克隆代码
git clone <repo-url> D:\sps-system
cd D:\sps-system\backend

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并重命名）
copy .env.example .env
# 编辑 .env 文件，修改数据库连接等信息

# 初始化数据库
alembic upgrade head
```

### `.env` 配置示例

```ini
DATABASE_URL=postgresql+asyncpg://scp:scp2026@localhost:5432/scp_db
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:5173
DEBUG=false
```

---

## 4. 前端部署

```powershell
cd D:\sps-system\frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 产物在 dist/ 目录
```

---

## 5. 启动方式

### 5.1 开发模式（调试用）

```powershell
# 后端
cd D:\sps-system\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload

# 前端（另一个终端）
cd D:\sps-system\frontend
npm run dev
```

### 5.2 生产模式

```powershell
# 后端
cd D:\sps-system\backend
.\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 6. 使用 NSSM 注册为 Windows 服务

NSSM (Non-Sucking Service Manager) 可将 Python 进程注册为 Windows 服务。

### 6.1 安装 NSSM

```powershell
# 下载 NSSM
# https://nssm.cc/download
# 解压到 C:\nssm

# 注册后端服务
C:\nssm\nssm.exe install SPSBackend
# Application 路径: D:\sps-system\backend\venv\Scripts\uvicorn.exe
# Arguments: app.main:app --host 0.0.0.0 --port 8000 --workers 4
# Startup directory: D:\sps-system\backend
# 点击 Install service
```

### 6.2 管理服务

```powershell
# 启动
net start SPSBackend

# 停止
net stop SPSBackend

# 查看状态
sc query SPSBackend

# 卸载
C:\nssm\nssm.exe remove SPSBackend confirm
```

---

## 7. Nginx 反向代理（可选）

```powershell
# 下载 Nginx for Windows
# https://nginx.org/en/download.html
# 解压到 C:\nginx

# 编辑配置 C:\nginx\conf\nginx.conf
```

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root D:/sps-system/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```powershell
# 启动 Nginx
cd C:\nginx
nginx.exe
# 访问 http://localhost
```

---

## 8. 备份

```powershell
# 数据库备份脚本 backup.bat
@echo off
set DATE=%date:~-4%%date:~-10,2%%date:~-7,2%
pg_dump -U scp -d scp_db > D:\backups\scp_db_%DATE%.sql
echo Backup completed: %DATE%
```

添加到任务计划程序定期执行。
