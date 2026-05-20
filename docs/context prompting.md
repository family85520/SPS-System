好，下面用一个完整的模拟场景来演示。

---

## 场景假设

假设你已经完成了阶段二的任务 2.1~2.4（班次模板后端+前端、约束规则后端+前端），此时当前对话的上下文已经快满了，你需要开一个新对话继续开发任务 2.5（特殊角色排班规则后端）。

---

## 在当前对话结束前，让我生成对话摘要

你在当前对话中对我说：

> 请生成本次对话摘要，我要保存下来用于下一个新对话中衔接开发。

我会输出类似这样的摘要：

```
【对话摘要 - 2026年5月16日】

一、本次完成：
1. 任务2.1：班次模板管理后端
   - 新建文件：app/api/shift_template.py, app/schemas/shift_template.py, app/services/shift_template_service.py
   - 实现7个API接口（CRUD + 复制 + 状态切换）
   - 已注册路由到main.py

2. 任务2.2：班次模板管理前端
   - 新建文件：src/api/shift-template.ts, src/views/shift-template/ShiftTemplateView.vue
   - 实现左右分栏布局（列表+编辑表单）
   - 路由已更新

3. 任务2.3：约束规则管理后端
   - 新建文件：app/api/constraint.py, app/schemas/constraint.py, app/services/constraint_service.py, app/models/constraint.py
   - 新增sch_constraint表（需执行数据库同步）
   - 实现7个API接口
   - init_data.py中增加了8条预置规则初始化

4. 任务2.4：约束规则管理前端
   - 新建文件：src/api/constraint.ts, src/views/constraint/ConstraintView.vue
   - 实现左右分栏布局（规则列表+详情编辑）
   - 拖拽排序优先级

二、需要执行的数据库操作：
   - 重启后端服务即可自动创建sch_constraint表（init_db会自动建表）

三、修改的文件：
   - app/main.py（注册constraint路由）
   - app/models/__init__.py（导出SchConstraint）
   - app/utils/init_data.py（增加预置约束规则）
   - src/router/index.ts（更新路由）

四、已知问题：
   - 无

五、下一步：任务2.5 特殊角色排班规则后端
```

---

## 在新对话中发送的内容

打开一个新的对话窗口，把以下内容**完整粘贴**发送：

```
我在开发一个排班管理系统，技术栈是 Python FastAPI + Vue3 + TypeScript + Element Plus + PostgreSQL。

数据库信息：
- 数据库名称：scp_db
- 用户名：scp
- 密码：scp2026
- 地址：localhost:5432

项目路径：
- 后端：D:\学习资料\JS\SPS-System\backend
- 前端：D:\学习资料\JS\SPS-System\frontend

后端默认管理员账号：admin / admin123

【当前进度】
已完成的任务：2.1、2.2、2.3、2.4
当前开发任务：2.5（特殊角色排班规则后端）

【对话摘要】
1. 任务2.1：班次模板管理后端
   - 新建文件：app/api/shift_template.py, app/schemas/shift_template.py, app/services/shift_template_service.py
   - 实现7个API接口（CRUD + 复制 + 状态切换）
   - 已注册路由到main.py

2. 任务2.2：班次模板管理前端
   - 新建文件：src/api/shift-template.ts, src/views/shift-template/ShiftTemplateView.vue
   - 实现左右分栏布局（列表+编辑表单）
   - 路由已更新

3. 任务2.3：约束规则管理后端
   - 新建文件：app/api/constraint.py, app/schemas/constraint.py, app/services/constraint_service.py, app/models/constraint.py
   - 新增sch_constraint表
   - 实现7个API接口
   - init_data.py中增加了8条预置规则初始化

4. 任务2.4：约束规则管理前端
   - 新建文件：src/api/constraint.ts, src/views/constraint/ConstraintView.vue
   - 拖拽排序优先级

修改的文件：main.py, models/__init__.py, init_data.py, router/index.ts
已知问题：无

请继续开发任务2.5：特殊角色排班规则后端。
任务要求如下：
- 新建文件：app/api/special_rule.py, app/schemas/special_rule.py, app/services/special_rule_service.py
- API接口：GET列表、GET详情、POST创建、PUT更新、DELETE删除
- 支持6种规则类型：exclude_shift、include_shift、exclude_post、must_pair、exclude_date、exclude_weekday
- 有有效期字段（effective_from, effective_to）
- 注册路由到main.py

请直接输出代码。
```

---

## 输出格式

【代码块要求】
对应代码块使用对应的编程代码块分隔

**查找 `XXX/XXX/XXX.py`文件（X处查找替换）**

**查找：**
```
AAA
```

**替换为：**
```
AAAXXX
```

**新建 `XXX/XXX/XXX.py`文件**

**新建文件：**

```
XXXXX
```
---

## 效果

新对话中的我收到这段消息后，能够：

1. **理解项目背景**：排班系统、技术栈、数据库信息
2. **知道当前进度**：任务2.1~2.4已完成，接下来做2.5
3. **了解已有代码结构**：通过对话摘要知道已经建了哪些文件
4. **明确本次需求**：任务2.5的具体要求
5. **直接输出代码**：不需要再重复讨论需求和架构

---

## 模板（通用版）

你可以把以下模板保存下来，每次上下文快满时套用：

```
我在开发一个排班管理系统，技术栈是 Python FastAPI + Vue3 + TypeScript + Element Plus + PostgreSQL。

数据库：scp_db / scp / scp2026 / localhost:5432
后端路径：D:\学习资料\JS\SPS-System\backend
前端路径：D:\学习资料\JS\SPS-System\frontend

【已完成任务】列出任务编号
【当前任务】任务编号和名称
【对话摘要】列出本次完成的内容、新建的文件、修改的文件、已知问题
【下一步需求】具体要开发什么

请直接输出代码。
```

---

## 额外建议：保存关键文件

除了对话摘要，建议你平时把以下信息保存在一个本地文件中（比如 `docs/ProjectStatus.md`），随时更新：

```markdown
# 项目状态

## 数据库
- 名称：scp_db
- 用户：scp / scp2026

## 已完成
- [x] 1.1 项目骨架搭建
- [x] 1.2 数据库模型
- [x] 1.3 用户认证
- [x] 1.4 组织架构API
- [x] 1.5 人员管理API
- [x] 2.1 班次模板后端
- [x] 2.2 班次模板前端
- [x] 2.3 约束规则后端
- [x] 2.4 约束规则前端

## 进行中
- [ ] 2.5 特殊角色规则后端

## 待开发
- [ ] 2.6 特殊角色规则前端
- [ ] 2.7 角色权限后端
- [ ] 2.8 角色权限前端
- [ ] 2.9 系统配置
- [ ] 3.1~3.7 排班核心
- [ ] 4.1~4.4 消息+看板
- [ ] 5.1~5.2 调班管理
- [ ] 6.1~6.3 移动端+导出
- [ ] 7.1~7.4 部署+测试

## 已知问题
（暂无）
```

这样在任何新对话中，只需发送这个文件内容 + 你的具体需求即可。

---
