# 排班引擎 V2 设计文档

**日期**: 2026-06-13
**范围**: 跨月替换规则重构、配对关系持久化、一致性保证

---

## 1. 问题背景

当前排班引擎存在以下问题：
- 跨月替换规则不正确（特殊人员组替换逻辑错误）
- 逐月生成和多月生成结果不一致
- 手动调整后自动生成无法正确继承调整结果

## 2. 核心规则（从参考排班表推导）

### 2.1 人员分组

**特殊人员池**: [冯绍晏(A006), 罗士发(abm_202605001)]

**班次模板**:
- 白班/夜班模板: 12人 = 1特殊 + 11普通 (3槽位×4人)
- 行政模板: 3人 = 1特殊 + 2普通

### 2.2 跨月轮换规则

```
月A: 白班/夜班 = [罗士发(特殊)] + [保雄智,罗雄伟(普通配对)]
     行政     = [冯绍晏(特殊)] + [肖普,蔡文星(普通配对)]

         ↓ 跨月轮换 ↓

月B: 白班/夜班 = [冯绍晏(特殊)] + [肖普,蔡文星(普通配对)]
     行政     = [罗士发(特殊)] + [保雄智,罗雄伟(普通配对)]
```

**规则**:
1. 特殊人员在两个班次间交替轮换
2. 普通人员跟随特殊人员移动（上月行政普通→本月白班/夜班，反之亦然）
3. 新老配对关系保持稳定，仅在特殊轮换时重新绑定

### 2.3 配对关系规则

- 新老员工绑定后保持稳定，跨月不变
- 只有当特殊轮换选中配对中的人员时，才重新绑定
- 配对关系存储在数据库中，手动调整时自动更新

### 2.4 一致性保证

- 所有跨月状态从数据库推导，不依赖内存
- 逐月生成和多月生成使用相同逻辑
- 首次生成时按新老搭配规则建立配对

### 2.5 重新生成规则

- 只能重新生成未发布排班
- 已存在未发布排班 → 询问用户是否覆盖
- 已发布排班 → 不可重新生成

---

## 3. 数据库设计

### 3.1 新增表：sch_pairing

```sql
CREATE TABLE sch_pairing (
    id SERIAL PRIMARY KEY,
    org_id INT NOT NULL,
    shift_id INT NOT NULL,
    slot_index INT NOT NULL,
    group_type VARCHAR(10) NOT NULL,
    staff_ids INT[] NOT NULL,
    is_new BOOLEAN[] NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, shift_id, slot_index, group_type)
);
```

**字段说明**:
- `org_id`: 组织ID
- `shift_id`: 班次模板ID
- `slot_index`: 槽位索引 (0/1/2)
- `group_type`: "day" 或 "night"
- `staff_ids`: 配对人员ID数组 [新员工, 老员工]
- `is_new`: 对应是否新员工

### 3.2 SQLAlchemy 模型

```python
# backend/app/models/pairing.py
from sqlalchemy import String, Integer, ARRAY, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import TimestampMixin

class SchPairing(Base, TimestampMixin):
    __tablename__ = "sch_pairing"
    __table_args__ = (
        UniqueConstraint('org_id', 'shift_id', 'slot_index', 'group_type'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shift_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    group_type: Mapped[str] = mapped_column(String(10), nullable=False)
    staff_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    is_new: Mapped[list[bool]] = mapped_column(ARRAY(Boolean), nullable=False)
```

---

## 4. 核心流程设计

### 4.1 自动生成流程

```
auto_generate(start_date, end_date):
  1. 检查目标月份是否有未发布排班
     - 有 → 询问用户是否覆盖
     - 无 → 继续

  2. 从 sch_pairing 读取上月配对关系
     - 有 → 使用
     - 无 → 从上月排班记录推导
     - 上月也无 → 按新老搭配规则新建

  3. 从上月排班记录推导特殊人员轮换状态
     - 确定上月每个班次的特殊人员是谁
     - 确定本月应该轮换到哪个班次

  4. 执行当月排班：
     - 特殊人员轮换（交替班次）
     - 普通人员按配对关系分配
     - 新老配对保持稳定

  5. 保存结果 + 更新 sch_pairing
```

### 4.2 手动调整流程

```
manual_adjust(schedule_id, changes):
  1. 更新排班记录
  2. 检查是否影响配对关系
     - 影响 → 更新 sch_pairing
     - 不影响 → 不变
```

### 4.3 配对关系管理

```
PairingManager:
  - get_pairing(org_id, shift_id, slot_index, group_type)
  - set_pairing(org_id, shift_id, slot_index, group_type, staff_ids, is_new)
  - derive_from_schedule(org_id, month)  # 从排班记录推导配对
  - update_on_adjust(schedule_id, changes)  # 手动调整时更新
```

---

## 5. 关键文件

| 文件 | 职责 |
|---|---|
| `backend/app/models/pairing.py` | 配对关系模型（新增）|
| `backend/app/engine/pairing_manager.py` | 配对管理器（新增）|
| `backend/app/engine/scheduler.py` | 排班引擎核心（修改）|
| `backend/app/services/schedule_service.py` | 排班服务（修改）|
| `backend/app/api/schedule.py` | 排班API（修改）|

---

## 6. 动态变化处理

### 6.1 人员减少（离职/调岗）

- 保留配对标记，不删除 sch_pairing 记录
- 下次自动生成时，检测到配对中人员不在可用列表中
- 自动从可用人员中选择替补，按新老搭配规则重新绑定

### 6.2 人员新增

- 新员工自动按新老搭配规则插入到缺人的配对中
- 如果没有空缺配对，按规则自动生成新的槽位
- 根据班次模板配置，自动补充到对应班次位置

### 6.3 特殊人员池变更

- **新增特殊人员**：追加到 special_pool 队列末尾，等待轮换
- **移除特殊人员**：普通人员保持原配对不变，等待下次特殊轮换时重新绑定

### 6.4 班次人数变更

- **增加人数**：扩大现有槽位（每槽位人数增加）
- **减少人数**：缩小现有槽位（每槽位人数减少）
- 槽位数量保持不变，仅调整每槽位的人数

---

## 7. 验证方案

1. **逐月生成测试**: 逐月生成6-9月排班，与参考排班表对比
2. **多月生成测试**: 多月生成6-9月排班，与逐月生成结果对比
3. **手动调整测试**: 手动调整7月排班后生成8月，验证配对关系正确
4. **重新生成测试**: 测试重新生成已存在未发布排班的询问流程
5. **一致性测试**: 确保两种生成方式结果完全一致
