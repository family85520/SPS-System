# 排班引擎全面优化设计文档

**日期**: 2026-06-11
**方案**: 渐进式修复 + 泛化（方案 A）
**范围**: Bug 修复、槽位绑定泛化、约束规则补全、清理与可配置化

---

## 1. Bug 修复

### 1.1 `publish_schedules` 方法名错误

**文件**: `backend/app/services/auto_schedule_job.py` 第 93 行

**问题**: 调用了 `ScheduleService.publish_schedules()`，但实际方法名是 `ScheduleService.publish()`，自动发布时会抛出 `AttributeError`。

**修复**: 将 `publish_schedules()` 改为 `publish()`。

### 1.2 跨月连续工作天数计算缺陷

**文件**: `backend/app/engine/scheduler.py` 第 160 行

**问题**: `_will_exceed_continuous` 只从 `_run_start_str` 开始计算连续天数，不考虑上月末尾的工作记录。如果某人上月最后 4 天都在工作，本月第 1 天仍可被分配，导致实际连续 5+ 天。

**修复方案**:
1. 在 `ScheduleService.auto_generate()` 中，加载上月最后 `MAX_CONTINUOUS_DAYS` 天的历史排班数据
2. 将这些数据作为"前序历史"传入 `AutoScheduler`
3. `_will_exceed_continuous` 在计算连续天数时，将前序历史与当月数据合并计算

**数据结构**:
```python
# AutoScheduler 新增属性
self._pre_history: dict[int, list[str]] = {}  # staff_id -> [date_str, ...]
```

### 1.3 Swap 请求被激进删除

**文件**: `backend/app/services/schedule_service.py` 第 1193-1200 行

**问题**: 自动排班清理旧排班时，连带删除了所有关联的 swap 请求，包括进行中的。

**修复**: 只删除已完成（completed）或已取消（cancelled）的 swap 请求，保留进行中的请求。如果存在进行中的 swap 请求且关联的排班将被删除，跳过该排班的删除并记录警告。

---

## 2. 槽位绑定系统泛化

### 2.1 核心算法

当前系统只支持 N=12 的硬编码逻辑。泛化后支持 N=10~14 的动态分组。

**槽位分配策略**:
```
输入: N 个候选人（按 ID 排序）
槽位数: 3（固定）
每槽位人数: ⌈N/3⌉ 或 ⌊N/3⌋（尽量均匀）

N=12: 每槽 4 人（2+2），完美对称
N=10: 槽位 4/3/3
N=11: 槽位 4/4/3
N=13: 槽位 5/4/4
N=14: 槽位 5/5/4
```

**槽位内部分组**:
- 每个槽位分为 `day_group` 和 `night_group`
- 偶数人数: 平分（4→2+2, 6→3+3）
- 奇数人数: `day_group` 多 1 人（5→3+2）

### 2.2 新老搭配

**识别方式**: 通过 Tag/Role 标记区分新老员工

**配对逻辑**:
1. 按 Tag/Role 标记将候选人分为 `new_ids` 和 `old_ids`
2. 交叉配对: 优先 1 新 + 1 老
3. 剩余同类人员自行配对
4. 配对结果分配到各槽位（每槽位 2 对）

### 2.3 白夜交替

```
rotation_slot = (day - 1) % 3        # 槽位编号 0/1/2
rotation_number = (day - 1) // 3     # 轮换编号

偶数 rotation_number:
  day_group → 白班, night_group → 夜班

奇数 rotation_number:
  day_group → 夜班, night_group → 白班
```

### 2.4 月度绑定

- 同一槽位的 4 人（day_group + night_group）整月固定
- 不跨槽混搭
- 每人每月约 5 白 + 5 夜（30 天月，3 槽位 × 10 轮换）

### 2.5 跨月替换机制

**规则**:
1. **特殊人员组内替换**: 特殊人员离开 → 从特殊人员组中选替补，进入原槽位
2. **普通人员替换**: 普通人员离开 → 从普通候选人中选替补，进入原槽位
3. **替换后班次不变**: 替补人员继承被替换者的预设班次（白/夜分配不变）

**流程**:
```
月 A 槽位: [A, B] [C, D] [E, F]
月 B 人员变更: B 离开，G 加入
月 B 槽位: [A, G] [C, D] [E, F]
→ G 进入 B 的原位置，保持白/夜分配不变
```

### 2.6 多月生成 vs 逐月生成

- **多月一次生成**: 每月开头重置 `_bound_groups`，但保留跨月历史数据
- **逐月生成**: 每次调用 `auto_generate` 只生成一个月，历史数据从数据库加载
- 两种方式使用相同的槽位分配逻辑，确保结果一致

---

## 3. 约束规则补全

### 3.1 HOLIDAY_MODE（节假日模式）

**功能**: 节假日期间的特殊排班规则

**配置参数**:
```json
{
  "mode": "increase",
  "extra_count": 2
}
```
或
```json
{
  "mode": "fixed",
  "staff_ids": [1, 2, 3]
}
```

**模式说明**:
- `increase`: 节假日比平时多排 N 人
- `fixed`: 节假日固定安排指定人员

**实现**: 在 `ConstraintChecker.check_holiday_mode()` 中，检测日期是否为节假日（从数据库 `SysHoliday` 表加载），检查排班人数是否符合要求。

### 3.2 WEEKEND_DIFF（周末差异化）

**功能**: 周末排班与工作日排班的差异化规则

**配置参数**:
```json
{
  "mode": "different_shift",
  "weekend_shift_ids": [1, 2]
}
```
或
```json
{
  "mode": "reduced",
  "reduced_count": 1
}
```

**模式说明**:
- `different_shift`: 周末使用不同的班次模板
- `reduced`: 周末减少排班人数

**实现**: 在 `ConstraintChecker.check_weekend_diff()` 中，检测日期是否为周末，检查排班是否符合差异化要求。

### 3.3 MIN_REST_AFTER_CONTINUOUS（连续工作后最小休息）

**功能**: 连续工作 N 天后，必须休息 M 天

**配置参数**:
```json
{
  "continuous_days": 5,
  "rest_days": 2
}
```

**实现**: 在 `ConstraintChecker` 中，检查每个人在连续工作 N 天后，是否安排了至少 M 天休息。与 `MAX_CONTINUOUS_DAYS` 配合使用。

---

## 4. 清理与可配置化

### 4.1 清理死代码

- 删除 `scheduler.py` 中的 `_tier_rotate_select` 方法（未被调用）
- 清理相关的诊断日志代码

### 4.2 FairnessScorer 权重可配置化

**当前状态**: 权重硬编码在 `scoring.py` 中

**设计方案**:
- 在 `SchConstraint` 表中新增约束类型 `FAIRNESS_WEIGHTS`
- 参数格式:
```json
{
  "weight_hours": 0.3,
  "weight_night": 3.0,
  "weight_weekend": 2.0,
  "penalty_same_day": 1000.0,
  "penalty_consecutive": 50.0,
  "penalty_gap_1_day": 25.0,
  "penalty_gap_2_day": 10.0,
  "penalty_same_shift_type": 30.0
}
```
- `FairnessScorer` 初始化时从约束配置读取权重，未配置则使用默认值
- 前端在约束管理页面可配置

---

## 5. 实施顺序

1. **阶段 1: Bug 修复** (1.1, 1.2, 1.3)
2. **阶段 2: 槽位绑定泛化** (2.1 ~ 2.6)
3. **阶段 3: 约束规则补全** (3.1, 3.2, 3.3)
4. **阶段 4: 清理与可配置化** (4.1, 4.2)

---

## 6. 不修改的部分

- Leader 候选人全局排除逻辑（保持现状）
- DutyTeam 模型（本次不启用引擎支持）
- 双 Tag 系统（本次不统一）
- 前端 comma-separated ID 传递方式（本次不改）
