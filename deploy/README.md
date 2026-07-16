# SPS 排班管理系统 — 部署脚本

## 快速开始

### Linux (Ubuntu/CentOS)

```bash
# 1. 生成环境配置（交互式）
sudo bash deploy/linux/deploy.sh setup-env

# 2. 初始化数据库
sudo bash deploy/linux/deploy.sh setup-db

# 3. 一键完整部署
sudo bash deploy/linux/deploy.sh deploy --domain your-domain.com

# 4. 查看服务状态
sudo bash deploy/linux/deploy.sh status

# 5. 数据库备份
sudo bash deploy/linux/deploy.sh backup
```

### Windows

```powershell
# 1. 生成环境配置
.\deploy\windows\deploy.ps1 -Mode setup-env

# 2. 初始化数据库
.\deploy\windows\deploy.ps1 -Mode setup-db

# 3. 构建项目
.\deploy\windows\deploy.ps1 -Mode build

# 4. 注册为 Windows 服务（需要 NSSM）
.\deploy\windows\deploy.ps1 -Mode nssm-install

# 5. 启动服务
.\deploy\windows\deploy.ps1 -Mode start

# 6. 查看状态
.\deploy\windows\deploy.ps1 -Mode status
```

## 可用命令

| 命令 | 说明 | Linux | Windows |
|------|------|-------|---------|
| `install` | 安装系统依赖 + Python venv + 前后端依赖 | ✅ | ✅ |
| `setup-db` | 创建数据库和用户 | ✅ | ✅ |
| `setup-env` | 交互式生成 .env 配置 | ✅ | ✅ |
| `build` | 前端 npm build + 后端 pip install | ✅ | ✅ |
| `deploy` | 完整部署流程（仅 Linux） | ✅ | ❌ |
| `start` | 启动后端服务 | ✅ | ✅ |
| `stop` | 停止后端服务 | ✅ | ✅ |
| `restart` | 重启后端服务 | ✅ | ✅ |
| `status` | 查看服务状态 + 健康检查 | ✅ | ✅ |
| `rollback` | 回滚到上一版本 | ✅ | ✅ |
| `backup` | 数据库备份 | ✅ | ✅ |
| `clean` | 清理构建产物 | ✅ | ✅ |
| `nssm-install` | 注册 Windows 服务 | ❌ | ✅ |
| `nssm-remove` | 卸载 Windows 服务 | ❌ | ✅ |

## 公共选项

| 选项 | 说明 |
|------|------|
| `--app-dir <path>` | 指定应用根目录 |
| `--domain <host>` | 域名（用于 Nginx） |
| `--force` | 强制覆盖已有配置 |
| `--dry-run` | 仅显示将要执行的命令 |
| `--verbose` | 详细日志输出 |
| `--skip-healthcheck` | 跳过健康检查（CI/CD） |

## 架构

```
deploy/
├── lib/                    # 共享工具库
│   ├── common.sh          # 日志、颜色、参数解析、健康检查
│   ├── db_helper.sh       # 数据库管理
│   ├── nginx_helper.sh    # Nginx 配置
│   └── systemd_helper.sh  # systemd 服务管理
├── linux/
│   └── deploy.sh          # Linux 统一入口
├── windows/
│   └── deploy.ps1         # Windows 统一入口
├── scripts/
│   ├── backup.sh          # 独立备份脚本（Linux）
│   └── backup.bat         # 独立备份脚本（Windows）
└── README.md              # 本文件
```

## 安全说明

1. **`.env` 文件权限**: 部署脚本自动设置为 `600`（仅所有者可读写）
2. **SECRET_KEY**: 自动生成，不硬编码
3. **数据库密码**: 全部从 `.env` 读取，脚本中不出现明文
4. **systemd 用户**: Linux 生产环境使用专用 `sps` 用户运行服务
5. **HTTPS**: 支持 certbot 一键申请证书 (`./deploy.sh deploy --enable-https`)

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| `python3.12 not found` | `sudo apt install python3.12 python3.12-venv` |
| `psql: command not found` | `sudo apt install postgresql-client` |
| `npm: command not found` | 安装 Node.js 20.x LTS |
| `NSSM not found` | 从 https://nssm.cc/download 下载并解压到 `C:\nssm` |
| 服务启动失败 | 查看日志: `journalctl -u sps-backend -f` (Linux) 或 `C:\nssm\logs\` (Windows) |
| 健康检查超时 | 检查防火墙: `sudo ufw allow 80/tcp` |

## 旧脚本迁移

以下旧脚本已被新脚本替代，可以安全删除：

- ~~`deploy/linux/install.sh`~~ → `deploy.sh install` + `deploy.sh setup-db`
- ~~`deploy/linux/start.sh`~~ → `deploy.sh start`
- ~~`deploy/windows/start.bat`~~ → `deploy.ps1 -Mode start`
