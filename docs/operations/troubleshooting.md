# 运维故障排查手册

**文档版本：** V1.0
**最后更新：** 2026-07-10
**维护者：** 运维团队

---

## 1. 快速诊断流程图

```
系统异常
  │
  ├─ 前端无法访问
  │   ├─ 检查 Nginx 是否运行
  │   ├─ 检查 dist/ 目录是否存在
  │   └─ 检查浏览器控制台错误
  │
  ├─ 后端 API 返回 500
  │   ├─ 查看后端日志
  │   ├─ 检查数据库连接
  │   └─ 检查磁盘空间
  │
  ├─ 数据库连接失败
  │   ├─ 检查 PostgreSQL 服务状态
  │   ├─ 检查 .env 配置
  │   └─ 检查防火墙规则
  │
  └─ 性能缓慢
      ├─ 检查 CPU/内存使用
      ├─ 检查数据库慢查询
      └─ 检查网络延迟
```

---

## 2. 常见问题及解决方案

### 2.1 后端无法启动

**症状：** uvicorn 启动报错或进程退出

**排查步骤：**

```bash
# 1. 查看进程状态
systemctl status sps-backend

# 2. 查看实时日志
journalctl -u sps-backend -f --since "10 minutes ago"

# 3. 检查端口占用
ss -tlnp | grep 8000

# 4. 检查虚拟环境
cd /opt/sps-system/backend
source venv/bin/activate
python -c "from app.main import app; print('OK')"
```

**常见错误：**

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `OperationalError: could not connect` | 数据库不可达 | 检查 PostgreSQL 服务和 .env 配置 |
| `error: [Errno 98] Address already in use` | 端口被占用 | `kill $(lsof -t -i:8000)` |

### 2.2 数据库迁移失败

**症状：** 启动时报错 `Table xxx already exists` 或 `column xxx does not exist`

**排查步骤：**

```bash
# 1. 查看当前迁移版本
cd /opt/sps-system/backend
source venv/bin/activate
alembic current

# 2. 查看所有可用版本
alembic history --verbose

# 3. 升级到最新版本
alembic upgrade head

# 4. 如果版本不一致，尝试降级后升级
alembic downgrade base
alembic upgrade head
```

### 2.3 JWT Token 失效

**症状：** 前端频繁跳回登录页，接口返回 401

**排查步骤：**

```bash
# 1. 检查 Token 过期时间配置
grep ACCESS_TOKEN_EXPIRE backend/app/config.py
# 默认 480 分钟（8 小时）

# 2. 检查服务器时间是否同步
timedatectl status

# 3. 清除浏览器缓存和 Cookie
# 按 F12 → Application → Clear Storage
```

### 2.4 WebSocket 连接不稳定

**症状：** 消息推送延迟或断连

**排查步骤：**

```bash
# 1. 检查 Nginx WebSocket 配置
grep -A5 "websocket" /etc/nginx/sites-enabled/sps-system

# 2. 检查超时设置
# proxy_read_timeout 应 >= 86400（24小时）

# 3. 检查后端日志中的 WebSocket 事件
journalctl -u sps-backend | grep -i websocket
```

### 2.5 自动排班未执行

**症状：** 月末自动排班未生成

**排查步骤：**

```bash
# 1. 检查自动排班配置
psql -U scp -d scp_db -c "SELECT * FROM sys_config WHERE config_key LIKE 'auto%';"

# 2. 检查 APScheduler 日志
journalctl -u sps-backend | grep -i "自动排班"

# 3. 验证调度器是否运行
curl http://localhost:8000/health
```

**配置键说明：**

| config_key | 说明 | 示例值 |
|-----------|------|--------|
| auto_schedule_enabled | 是否启用 | true/false |
| auto_schedule_status | 当前状态 | draft/published |
| auto_schedule_time | 触发时间 | 23:00 |
| auto_schedule_org_ids | 涉及组织 | 1,2,3 |
| auto_schedule_shift_ids | 涉及班次 | 1,2 |
| auto_schedule_skip_existing | 跳过已有 | true/false |
| auto_schedule_last_run | 上次执行日期 | 2026-07-10 |

**触发条件（需同时满足）：**
1. 今天是当月最后一天
2. 当前时间在配置时间的 ±30 分钟窗口内
3. 今天尚未执行过自动排班（检查 `auto_schedule_last_run`）

**常见问题：**
- **问题：** 为什么每天检查但没执行？
  **解答：** 只有月末最后一天才会执行，平时只检查不执行
- **问题：** 为什么执行了两次？
  **解答：** 检查 `auto_schedule_last_run` 是否被正确记录，或手动清理过配置
| auto_schedule_last_run | 上次执行日期 | 2026-07-10 |

**触发条件（需同时满足）：**
1. 今天是当月最后一天
2. 当前时间在配置时间的 ±30 分钟窗口内
3. 今天尚未执行过自动排班（检查 `auto_schedule_last_run`）

**常见问题：**
- **问题：** 为什么每天检查但没执行？
  **解答：** 只有月末最后一天才会执行，平时只检查不执行
- **问题：** 为什么执行了两次？
  **解答：** 检查 `auto_schedule_last_run` 是否被正确记录，或手动清理过配置

### 2.6 磁盘空间不足

```bash
# 1. 查看磁盘使用
df -h

# 2. 查看大文件
du -sh /var/log/* | sort -rh | head -10

# 3. 清理日志
journalctl --vacuum-time=7d    # 保留 7 天日志
find /var/log -name "*.log" -mtime +30 -delete

# 4. 清理数据库备份
find /opt/backups -name "*.sql" -mtime +30 -delete
```

---

## 3. 日志位置

| 组件 | 日志位置 |
|------|---------|
| 后端应用 | `journalctl -u sps-backend` |
| Nginx 访问 | `/var/log/nginx/access.log` |
| Nginx 错误 | `/var/log/nginx/error.log` |
| PostgreSQL | `/var/log/postgresql/postgresql-*.log` |
| 系统日志 | `/var/log/syslog` |

---

## 4. 紧急联系人

| 角色 | 联系方式 |
|------|---------|
| 运维负责人 | （待补充） |
| 开发负责人 | （待补充） |
| DBA | （待补充） |

---

## 5. 回滚方案

### 5.1 代码回滚

```bash
cd /opt/sps-system
git log --oneline -10
git checkout <commit-hash> -- backend/ frontend/
# 重新安装依赖
cd backend && source venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install && npm run build
sudo systemctl restart sps-backend
```

### 5.2 数据库回滚

```bash
cd /opt/sps-system/backend
source venv/bin/activate

# 降级到指定版本
alembic downgrade <version_hash>

# 或回退到上一个版本
alembic downgrade -1
```
