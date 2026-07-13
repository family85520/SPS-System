# 编码规范与提交规范

**文档版本：** V1.0
**最后更新：** 2026-07-10
**适用对象：** 全体开发人员

---

## 1. Python 后端规范

### 1.1 代码风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码风格
- 使用 4 空格缩进，每行不超过 120 字符
- 使用 Black 格式化代码（如已安装）

### 1.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块/包 | 小写 + 下划线 | `shift_template.py` |
| 类名 | 大驼峰 | `ScheduleService` |
| 函数/方法 | 小写 + 下划线 | `create_schedule()` |
| 常量 | 大写 + 下划线 | `MAX_CONTINUOUS_DAYS` |
| 私有属性 | 单下划线前缀 | `_internal_cache` |

### 1.3 类型注解

所有函数参数和返回值应包含类型注解：

```python
async def create_schedule(
    db: AsyncSession,
    data: dict[str, Any],
) -> SchSchedule:
    """创建排班记录。"""
    ...
```

### 1.4 文档字符串

使用 Google 风格文档字符串：

```python
def calculate_duration(start_time: str, end_time: str) -> float:
    """计算班次时长（小时）。

    Args:
        start_time: 起始时间，格式 HH:MM
        end_time: 结束时间，格式 HH:MM

    Returns:
        班次时长（小时），跨天自动 +24

    Raises:
        ValueError: 时间格式无效时抛出
    """
    ...
```

### 1.5 错误处理

- 使用具体的异常类型，避免裸 `except:`
- Service 层抛出 `ValueError` 携带业务错误信息
- API 层捕获 `ValueError` 转换为 HTTP 400

```python
# Service 层
try:
    record = await db.execute(select(...))
    if not record:
        raise ValueError("资源不存在")
except ValueError as e:
    await db.rollback()
    raise

# API 层
try:
    return await service_method(...)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### 1.6 事务管理

- `get_db()` 不再自动 commit
- 每个 Service 独立管理事务边界
- 使用 `async with factory() as db:` 确保资源释放

**注意：** 自动排班 Job (`auto_schedule_job.py`) 中使用独立的 `async_session_factory` 管理事务，与 API 请求的事务隔离。

### 1.7 定时任务规范

- 使用 APScheduler 管理后台任务
- 检查间隔不宜过短（推荐 5 分钟以上）
- 长时间任务应记录执行状态到 `sys_config` 表
- 增加防重复执行机制（如 `auto_schedule_last_run` 配置项）

---

## 2. TypeScript/Vue 前端规范

### 2.1 代码风格

- 使用 TypeScript 严格模式（`strict: true`）
- 组件使用 `<script setup lang="ts">` 语法
- 优先使用组合式 API（Composition API）

### 2.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `ShiftCell.vue` |
| 组件内部 | camelCase | `shiftData` |
| 类型/接口 | PascalCase | `ScheduleResponse` |
| 常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| 工具函数 | camelCase | `formatDate()` |

### 2.3 组件规范

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ScheduleItem } from '@/types'

interface Props {
  scheduleId: number
  readonly?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update', data: ScheduleItem): void
  (e: 'delete', id: number): void
}>()

const isLoading = ref(false)
</script>

<template>
  <div class="shift-cell">
    <!-- 模板内容 -->
  </div>
</template>

<style scoped lang="scss">
.shift-cell {
  // 样式
}
</style>
```

### 2.4 API 调用规范

- 所有 API 封装在 `src/api/` 目录下
- 文件名与后端 Router 一一对应
- 使用 Axios 拦截器统一处理错误

```typescript
// src/api/schedule.ts
import api from '@/api/index'
import type { ScheduleListResponse } from '@/schemas/schedule'

export function getScheduleList(params: ScheduleQueryParams) {
  return api.get<ScheduleListResponse>('/schedules', { params })
}
```

### 2.5 状态管理规范

- 使用 Pinia 进行状态管理
- Store 按业务模块划分
- 避免在 Store 中直接调用 API，使用 Actions

```typescript
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  
  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
  }
  
  return { token, login }
})
```

---

## 3. Git 提交规范

### 3.1 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### 3.2 Type 列表

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响运行） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具变动 |
| `perf` | 性能优化 |

### 3.3 示例

```bash
# 新功能
git commit -m "feat(schedule): add auto-generate endpoint"

# Bug 修复
git commit -m "fix(engine): correct cross-month rotation logic"

# 文档
git commit -m "docs(api): add endpoint summary document"

# 重构
git commit -m "refactor(auth): extract permission merge logic"
```

### 3.4 提交前检查清单

- [ ] 代码已通过类型检查（`npm run build` / `python -m py_compile`）
- [ ] 无调试代码（console.log、print 语句）
- [ ] 无硬编码密码或密钥
- [ ] 提交信息符合 Conventional Commits 规范

---

## 4. 分支管理

### 4.1 分支策略

```
main (生产分支)
  ├── feature/add-export-api (功能分支)
  ├── fix/cross-month-bug (修复分支)
  └── docs/update-readme (文档分支)
```

- **main**：始终可部署，所有变更通过 PR 合并
- **feature/***：新功能开发
- **fix/***：Bug 修复
- **docs/***：文档更新

### 4.2 合并流程

1. 从 `main` 创建功能分支
2. 在功能分支上开发并提交
3. 推送到远程并创建 Pull Request
4. 代码审查通过后合并到 `main`
5. 删除功能分支

---

## 5. 代码审查要点

| 检查项 | 说明 |
|-------|------|
| 功能正确性 | 代码是否实现了预期功能 |
| 安全性 | 有无 SQL 注入、XSS、敏感信息泄露 |
| 性能 | 有无 N+1 查询、大对象序列化、内存泄漏 |
| 可维护性 | 命名是否清晰、逻辑是否简洁、注释是否充分 |
| 测试覆盖 | 是否有对应的单元测试或集成测试 |
| 文档同步 | 是否需要更新 API 文档、数据库文档等 |
