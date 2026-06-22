# 排班引擎整合优化设计文档

**日期**: 2026-06-16
**来源**: 整合 06-11 全面优化设计 + 06-13 V2 跨月替换设计
**范围**: 四阶段渐进式实施，先正确性后改进

---

## 1. 背景与问题

### 1.1 当前状态

- `scheduler.py`（1529行）：排班引擎核心，包含槽位分组、候选人过滤、公平性打分
- `pairing_manager.py`：已实现，管理配对关系持久化
- `constraint_checker.py`（814行）：约束校验引擎，部分规则待完善
- `schedule_service.py`：已集成 PairingManager 和 prev_month_schedules

### 1.2 已知问题

1. **跨月替换规则不正确**（06-13 发现）：特殊人员组的跨月轮换逻辑有误
2. **逐月生成和多月生成结果不一致**（06-13 发现）
3. **手动调整后自动生成无法正确继承**（06-13 发现）
4. **节假日模式、周末差异化约束待实现**（06-11 发现）
5. **公平性打分权重硬编码**（06-11 发现）
6. **槽位绑定仅支持 N=12 硬编码**（06-11 发现）

### 1.3 文档关系

06-11 是通用优化方案（Bug修复 + 泛化 + 补全 + 可配置化），06-13 是针对实际业务场景的深度定制（跨月轮换 + 配对持久化）。06-13 的跨月轮换规则是 06-11 槽位泛化的前置条件——在规则不正确之前做泛化没有意义。

---

## 2. 实施阶段

### Phase 0: V2 跨月替换正确性（06-13 文档）

**优先级**: P0 — 必须先做，其他阶段依赖此正确性

**目标**: 修复跨月替换规则，确保逐月/多月生成一致，支持手动调整继承

#### 2.0.1 跨月轮换规则（从参考排班表推导）

```
月A: 白班/夜班 = [罗士发(特殊)] + [保雄智,罗雄伟(普通配对)]
月A: 行政      = [冯绍晏(特殊)] + [肖普,蔡文星(普通配对)]

         ↓ 跨月轮换 ↓

月B: 白班/夜班 = [冯绍晏(特殊)] + [肖普,蔡文星(普通配对)]
月B: 行政      = [罗士发(特殊)] + [保雄智,罗雄伟(普通配对)]
```

**三条规则**:
1. 特殊人员在两个班次间交替轮换
2. 普通人员跟随特殊人员移动（上月行政普通 → 本月白班/夜班，反之亦然）
3. 新老配对关系保持稳定，仅在特殊轮换时重新绑定

#### 2.0.2 配对关系持久化（已实现，需验证）

- `sch_pairing` 表已创建（`backend/app/models/pairing.py`）
- `PairingManager` 已实现（`backend/app/engine/pairing_manager.py`）
- `ScheduleService.auto_generate` 已集成 PairingManager
- **待验证**: 配对关系是否正确保存/加载/更新

#### 2.0.3 改进 derive_from_schedule 推导逻辑

当前 `PairingManager.derive_from_schedule` 是简化版（只取第一天数据）。需要改进为：

1. 分析连续多天的人员组合模式
2. 找出稳定的 2 人组（day_group + night_group）
3. 按槽位索引正确分配到 3 个槽位
4. 识别新员工（通过 tags 或入职时间）

#### 2.0.4 手动调整后的配对更新

- 手动调整排班后，检查是否影响配对关系
- 如果影响，更新 `sch_pairing` 表
- 确保后续自动生成使用调整后的配对

#### 2.0.5 验证方案

| 测试 | 内容 | 预期 |
|------|------|------|
| 逐月生成测试 | 逐月生成 6-9 月排班 | 与参考排班表一致 |
| 多月生成测试 | 多月一次生成 6-9 月 | 与逐月生成结果一致 |
| 手动调整测试 | 手动调整 7 月后生成 8 月 | 配对关系正确继承 |
| 重新生成测试 | 重新生成未发布排班 | 询问用户是否覆盖 |

**产出文件**: `backend/tests/test_pairing.py`, `backend/tests/test_cross_month_consistency.py`

---

### Phase 1: Bug 修复（06-11 文档 第 1 节）

**优先级**: P1 — 基础稳固，修复已知缺陷

#### 2.1.1 publish_schedules 方法名错误

- **文件**: `backend/app/services/auto_schedule_job.py` 第 93 行
- **问题**: 调用 `ScheduleService.publish_schedules()`，实际方法是 `publish()`
- **修复**: 改为 `publish()`

#### 2.1.2 跨月连续工作天数计算缺陷

- **文件**: `backend/app/engine/scheduler.py` 第 158 行
- **问题**: `_will_exceed_continuous` 只从 `_run_start_str` 开始计算，不考虑上月末尾
- **当前状态**: 已在 `schedule_service.py` 中实现 `pre_history` 加载（5.1 节），传入 AutoScheduler
- **待验证**: `CandidateFilter._will_exceed_continuous` 是否正确使用了 `pre_history`

#### 2.1.3 Swap 请求被激进删除

- **文件**: `backend/app/services/schedule_service.py` 第 1193-1200 行
- **问题**: 自动排班清理旧排班时，连带删除了所有关联的 swap 请求
- **修复**: 只删除已完成/已取消的 swap 请求，保留进行中的

---

### Phase 2: 槽位绑定泛化（06-11 文档 第 2 节）

**优先级**: P2 — 在 Phase 0 规则正确后进行

#### 2.2.1 动态槽位分配

当前 `SlotGrouper` 硬编码了 3 槽位、12 人场景。泛化后支持 N=10~14：

```
N=10: 槽位 4/3/3
N=11: 槽位 4/4/3
N=12: 槽位 4/4/4 (标准)
N=13: 槽位 5/4/4
N=14: 槽位 5/5/4
```

#### 2.2.2 新老搭配交叉配对

- 按 Tag/Role 标记区分新老员工
- 优先 1 新 + 1 老配对
- 剩余同类人员自行配对
- 配对结果均匀分配到各槽位

#### 2.2.3 月度绑定

- 同一槽位的人员整月固定
- 不跨槽混搭
- 每人每月约 5 白 + 5 夜（30 天月，3 槽位 × 10 轮换）

#### 2.2.4 多月生成 vs 逐月生成一致性

- 多月一次生成：每月开头重置 `_bound_groups`，保留跨月历史
- 逐月生成：每次调用 `auto_generate` 只生成一个月，历史从数据库加载
- 两种方式必须使用相同的槽位分配逻辑

---

### Phase 3: 约束规则补全（06-11 文档 第 3 节）

**优先级**: P3 — 锦上添花

#### 2.3.1 HOLIDAY_MODE（节假日模式）

- `_check_holiday_mode` 和 `_check_holiday_mode_single` 已存在但返回空
- 实现逻辑：检测日期是否为节假日（从数据库加载），检查排班人数是否符合要求
- 配置参数：`mode: "increase"`（多排 N 人）或 `"fixed"`（固定安排指定人员）

#### 2.3.2 WEEKEND_DIFF（周末差异化）

- `_check_weekend_diff` 和 `_check_weekend_diff_single` 已存在但返回空
- 实现逻辑：检测日期是否为周末，检查排班是否符合差异化要求
- 配置参数：`mode: "different_shift"`（不同班次模板）或 `"reduced"`（减少人数）

#### 2.3.3 MIN_REST_AFTER_CONTINUOUS（连续工作后最小休息）

- `_check_min_rest_after_continuous` 已实现（第 185 行）
- 验证：参数 `continuous_days` 和 `rest_days` 是否正确生效

---

### Phase 4: 清理与可配置化（06-11 文档 第 4 节）

**优先级**: P4 — 收尾工作

#### 2.4.1 清理死代码

- 检查 `scheduler.py` 中未被调用的方法（如 `_tier_rotate_select`，如果还存在）
- 清理无用的诊断日志代码

#### 2.4.2 FairnessScorer 权重可配置化

- 当前权重硬编码在 `scoring.py` 中
- 在 `SchConstraint` 表中新增约束类型 `FAIRNESS_WEIGHTS`
- 参数格式：
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

## 3. 文件变更总览

| 阶段 | 文件 | 变更类型 | 说明 |
|------|------|----------|------|
| Phase 0 | `backend/app/engine/pairing_manager.py` | 修改 | 改进 derive_from_schedule 推导逻辑 |
| Phase 0 | `backend/app/engine/scheduler.py` | 修改 | 修复跨月替换逻辑 |
| Phase 0 | `backend/tests/test_pairing.py` | 新增 | 配对关系单元测试 |
| Phase 0 | `backend/tests/test_cross_month_consistency.py` | 新增 | 一致性测试 |
| Phase 1 | `backend/app/services/auto_schedule_job.py` | 修改 | 修复方法名 |
| Phase 1 | `backend/app/services/schedule_service.py` | 修改 | 修复 Swap 清理逻辑 |
| Phase 2 | `backend/app/engine/scheduler.py` | 修改 | 槽位绑定泛化 |
| Phase 3 | `backend/app/engine/constraint_checker.py` | 修改 | 补全节假日/周末约束 |
| Phase 4 | `backend/app/engine/scheduler.py` | 修改 | 清理死代码 |
| Phase 4 | `backend/app/engine/scoring.py` | 修改 | 权重可配置化 |
| Phase 4 | 前端 | 修改 | 约束管理页面增加权重配置 |

---

## 4. 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| Phase 0 跨月轮换规则与现有逻辑冲突 | 高 | 先写一致性测试，再改代码 |
| 配对关系持久化影响已有排班数据 | 中 | 迁移脚本：从现有排班推导配对 |
| 槽位泛化改变已有排班结果 | 中 | 仅影响新排班，已发布排班不受影响 |
| 约束规则补全引入新校验失败 | 低 | 默认宽松模式，逐步收紧 |

---

## 5. 不修改的部分

- Leader 候选人全局排除逻辑（保持现状）
- DutyTeam 模型（本次不启用引擎支持）
- 双 Tag 系统（本次不统一）
- 前端 comma-separated ID 传递方式（本次不改）
- 调班申请状态机（本次不改）
