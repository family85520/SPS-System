# Task 1 Report: schedule 模块新增 import/export 权限 action

## 变更内容

**文件:** `D:\学习资料\SPS-System\backend\app\api\role.py`

### 变更 1 — schedule 模块 actions 列表（第 51 行）

```diff
- "actions": ["read", "create", "update", "delete", "publish", "approve"],
+ "actions": ["read", "create", "update", "delete", "publish", "approve", "import", "export"],
```

### 变更 2 — actions 规格表新增条目（第 75-76 行之后）

```diff
             {"key": "approve", "label": "审批"},
+            {"key": "import", "label": "导入"},
+            {"key": "export", "label": "导出"},
         ],
     }
```

## 验证结果

- **Python 语法检查:** 通过（`ast.parse` 返回 Syntax OK）
- **完整导入测试:** 因本地环境缺少 `python-jose` 等依赖未能完成全量导入，但语法层面确认无误。依赖安装后即可验证。

## 注意事项

1. 此次仅修改了权限规格表的声明数据，未涉及任何业务逻辑或前端改动。
2. 已存在的 `export` 模块（第 64-67 行，`"key": "export"`，label `"数据导出"`）与新增的 `schedule` 模块的 `"export"` action 互不冲突——前者是一个独立的顶层模块，后者是 `schedule` 模块的一个操作权限 key。
3. 后续 Task 2/3 需要在前端使用这两个新的 action key 来渲染权限复选框和实现实际的导入导出功能。

## 状态

**DONE**
