# 排班引擎整合优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 验证 Phase 1-4 的已有实现是否正确，修复 Phase 0 跨月替换逻辑中的核心问题，改进 derive_from_schedule 推导逻辑，编写完整测试套件

**Architecture:** 四阶段渐进式：Phase 0（跨月替换正确性）→ Phase 1（Bug 验证）→ Phase 2（槽位泛化验证）→ Phase 3-4（约束补全+可配置化验证）。大部分 Bug 修复和约束补全已在代码中实现，重点是验证正确性和修复 Phase 0 的核心问题。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, pytest-asyncio

---

## 现状评估

经过代码审查，大部分 06-11 文档中标记为"待实现"的功能实际上已经完成：

| 功能 | 06-11 状态 | 当前实际状态 |
|------|-----------|-------------|
| publish_schedules 方法名 | Bug | **已修复** (auto_schedule_job.py:91) |
| 跨月连续天数计算 | Bug | **已实现** (pre_history 机制) |
| Swap 请求清理 | Bug | **已修复** (只删 completed/cancelled) |
| HOLIDAY_MODE 约束 | 待实现 | **已实现** (constraint_checker.py:654) |
| WEEKEND_DIFF 约束 | 待实现 | **已实现** (constraint_checker.py:723) |
| FairnessScorer 权重配置 | 待实现 | **已实现** (scoring.py:26-39) |
| 槽位绑定泛化 | 进行中 | **部分实现** (SlotGrouper 支持动态分组) |
| 配对持久化 | 新增 | **已实现** (pairing_manager.py) |

**Phase 0 是唯一需要重点修复的阶段**——跨月替换逻辑仍有问题。

---

## Phase 0: 跨月替换正确性

### Task 0.1: 分析当前 _assign_special_group 跨月轮换逻辑

**Files:**
- Modify: `backend/app/engine/scheduler.py` (443-631 行)

**背景:** `_assign_special_group` 方法当前通过 `_derive_special_from_other_shifts` 从其他班次推导特殊人员，但推导逻辑有问题。根据 06-13 文档，正确规则是：

```
月A: 白班特殊人员 = [罗士发] → 月B: 白班特殊人员 = [冯绍晏]（来自行政班）
月A: 行政特殊人员 = [冯绍晏] → 月B: 行政特殊人员 = [罗士发]（来自白班）
```

即：特殊人员在**不同班次模板**间交替轮换，而不是在同一个 special_pool 内轮换。

**步骤:**

- [ ] **Step 1: 阅读并理解当前 _derive_special_from_other_shifts 逻辑**

  查看 `scheduler.py` 第 511-553 行的 `_derive_special_from_other_shifts` 方法。该方法尝试从"其他班次"推导特殊人员，但问题是：
  - 它查找的是 `special_pool` 相同的班次模板
  - 但它没有正确区分"同一组"（白班/夜班）和"不同组"（行政）
  - `_derive_prev_special_from_db` 使用 Counter 取最频繁出现的特殊人员，这在人员被其他角色占用时会出错

- [ ] **Step 2: 修复 _assign_special_group 方法**

  修改 `scheduler.py` 第 443-509 行的 `_assign_special_group` 方法，实现正确的跨月轮换逻辑：

  ```python
  def _assign_special_group(
      self,
      shift: SchShiftTemplate,
      date_str: str,
      already_assigned: list[int],
      daily_assigned: set[int] | None = None,
  ) -> tuple[list[int], list[str]]:
      """分配特殊人员组 - 跨月交替轮换

      规则：
      1. 找到同一 special_pool 的其他班次模板
      2. 从上月的"其他班次"中推导本月特殊人员
      3. 如果没有其他班次数据，按 ID 顺序轮换
      """
      conflicts: list[str] = []
      special_pool = sorted(shift.special_pool or [])
      count = shift.special_count

      if not special_pool or not shift.special_enabled:
          return [], conflicts

      daily = daily_assigned or set()

      # 从其他班次的上月特殊人员推导
      new_members = self._derive_special_from_other_shifts(shift, special_pool)

      if new_members is None:
          # 首次生成或无上月数据：按 ID 顺序选择
          new_members = special_pool[:count]

      # 过滤并选择可用人员
      selected: list[int] = []
      assigned_set = set(already_assigned)
      for sid in new_members:
          if sid in assigned_set:
              conflicts.append(f"[诊断] {shift.name}：特殊人员(ID:{sid})已被分配，跳过")
              continue
          if sid in daily:
              conflicts.append(f"[诊断] {shift.name}：特殊人员(ID:{sid})当天已排其他班次，跳过")
              continue
          if sid not in self.staff_map:
              conflicts.append(f"{date_str} {shift.name}：特殊人员池中人员(ID:{sid})不在本组织中，已跳过")
              continue
          selected.append(sid)
          assigned_set.add(sid)

      if len(selected) < count:
          conflicts.append(f"{date_str} {shift.name}：特殊人员组可用人数不足，需{count}人，仅{len(selected)}人可用")

      # 保存当月特殊人员状态供后续推导使用
      self._prev_special_members[shift.id] = selected

      return selected, conflicts
  ```

- [ ] **Step 3: 修复 _derive_prev_special_from_db 方法**

  当前方法（第 555-604 行）使用 Counter 统计特殊人员池成员的出现频率，但这不准确。应该改为从 `self._prev_special_members` 缓存中直接读取上月结果：

  ```python
  def _derive_prev_special_from_db(self, shift: SchShiftTemplate) -> list[int] | None:
      """从内存缓存读取上月特殊人员（由 _assign_special_group 保存）"""
      return self._prev_special_members.get(shift.id, None) or None
  ```

  如果 `prev_month_schedules` 为空（首次生成），返回 None，由调用方处理。

- [ ] **Step 4: 修复 _derive_special_from_other_shifts 方法**

  当前方法的问题是它查找的是"相同 special_pool"的班次。正确做法是：找到同一组织下、使用相同 special_pool 的其他班次模板的上月特殊人员。

  ```python
  def _derive_special_from_other_shifts(self, current_shift: SchShiftTemplate, pool: list[int]) -> list[int] | None:
      """从上月其他班次推导本月特殊人员

      规则：特殊人员在不同班次间交替轮换。
      上月在白班/夜班的特殊人员，本月应在行政班；
      上月在行政班的特殊人员，本月应在白班/夜班。
      """
      if not self.prev_month_schedules:
          return None

      pool_set = set(pool)
      count = current_shift.special_count

      # 遍历上月所有排班记录，找出使用相同 special_pool 的其他班次
      for prev_sched in self.prev_month_schedules:
          if prev_sched.shift_id == current_shift.id:
              continue
          other_shift = self.shift_templates.get(prev_sched.shift_id)
          if not other_shift or not other_shift.special_enabled:
              continue
          other_pool = set(other_shift.special_pool or [])
          if other_pool != pool_set:
              continue

          # 找到同 pool 的其他班次，取其上月特殊人员
          # 这些人员本月应该轮换到当前班次
          return [d.staff_id for d in self.existing_details
                  if d.schedule_id == prev_sched.id][:count]

      return None
  ```

- [ ] **Step 5: 验证语法**

  ```bash
  cd backend && python -c "import ast; ast.parse(open('app/engine/scheduler.py', encoding='utf-8').read()); print('OK')"
  ```

---

### Task 0.2: 改进 PairingManager.derive_from_schedule 推导逻辑

**Files:**
- Modify: `backend/app/engine/pairing_manager.py`

**背景:** 当前 `derive_from_schedule` 方法在 06-13 的实施计划中是一个简化版本（只取第一天数据）。需要改进为正确的推导逻辑。

但注意：当前 `pairing_manager.py` 中并没有 `derive_from_schedule` 方法——配对关系是通过 `_groups_to_pairings` 在 scheduler 中生成的。06-13 计划中的 `derive_from_schedule` 应该是从已有排班记录反推配对关系，用于首次生成或数据库迁移。

- [ ] **Step 1: 添加 derive_from_schedule 方法到 PairingManager**

  在 `backend/app/engine/pairing_manager.py` 中添加新方法：

  ```python
  async def derive_from_schedule(
      self,
      shift_id: int,
      month_start: date,
      month_end: date,
  ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
      """从上月排班记录推导配对关系

      通过分析连续多天的人员组合模式，找出稳定的槽位分组。

      Returns:
          {(slot_index, group_type): (staff_ids, is_new)}
      """
      from collections import defaultdict, Counter

      # 1. 加载上月排班记录
      schedules = list((await self.db.execute(
          select(SchSchedule).where(
              SchSchedule.org_id == self.org_id,
              SchSchedule.shift_id == shift_id,
              SchSchedule.date >= month_start,
              SchSchedule.date <= month_end,
          )
      )).scalars().all())

      if not schedules:
          return {}

      schedule_ids = [s.id for s in schedules]
      details = list((await self.db.execute(
          select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
      )).scalars().all())

      if not details:
          return {}

      # 2. 按日期分组人员
      day_staff: dict[str, list[int]] = defaultdict(list)
      schedule_map = {s.id: s for s in schedules}
      for d in details:
          s = schedule_map.get(d.schedule_id)
          if s:
              day_staff[str(s.date)].append(d.staff_id)

      if not day_staff:
          return {}

      # 3. 找出连续多天稳定出现的2人组（day_group 和 night_group）
      # 按日期排序，取前7天分析
      sorted_dates = sorted(day_staff.keys())[:7]
      if not sorted_dates:
          return {}

      # 4. 统计每对人一起出现的频率
      pair_cooccurrence: Counter = Counter()
      for date_str in sorted_dates:
          staff_on_day = day_staff[date_str]
          for i in range(len(staff_on_day)):
              for j in range(i + 1, len(staff_on_day)):
                  pair = tuple(sorted([staff_on_day[i], staff_on_day[j]]))
                  pair_cooccurrence[pair] += 1

      # 5. 提取高频配对（连续出现 >= 5 天的2人组）
      threshold = max(3, len(sorted_dates) // 2)
      stable_pairs = [(pair, count) for pair, count in pair_cooccurrence.items() if count >= threshold]
      stable_pairs.sort(key=lambda x: -x[1])

      if not stable_pairs:
          # 降级：取第一天数据简单分组
          return self._fallback_derive(day_staff, sorted_dates[0])

      # 6. 将配对分配到3个槽位
      # 每槽位需要 2 个配对（4人：2人day_group + 2人night_group）
      result = {}
      pair_idx = 0
      for slot_idx in range(3):
          if pair_idx + 1 >= len(stable_pairs):
              break
          day_pair = stable_pairs[pair_idx][0]
          night_pair = stable_pairs[pair_idx + 1][0]
          result[(slot_idx, "day")] = (list(day_pair), self._determine_new_status(day_pair))
          result[(slot_idx, "night")] = (list(night_pair), self._determine_new_status(night_pair))
          pair_idx += 2

      return result

  def _fallback_derive(
      self,
      day_staff: dict[str, list[int]],
      first_date: str,
  ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
      """降级方案：取第一天数据简单分组"""
      staff = day_staff.get(first_date, [])
      if not staff:
          return {}

      # 加载人员信息判断新老
      staff_list = list((await self.db.execute(
          select(OrgStaff).where(OrgStaff.id.in_(staff))
      )).scalars().all())
      staff_map = {s.id: s for s in staff_list}

      # 简单分组：前一半 day，后一半 night
      mid = len(staff) // 2
      day_group = staff[:mid]
      night_group = staff[mid:]

      result = {}
      # 均匀分配到3个槽位
      per_slot = max(1, len(day_group) // 3)
      for slot_idx in range(3):
          start = slot_idx * per_slot
          end = start + per_slot
          if start < len(day_group):
              result[(slot_idx, "day")] = (day_group[start:end], self._determine_new_status_list(day_group[start:end]))
          if start < len(night_group):
              result[(slot_idx, "night")] = (night_group[start:end], self._determine_new_status_list(night_group[start:end]))

      return result

  def _determine_new_status(self, staff_ids: tuple[int, ...]) -> list[bool]:
      """判断人员是否为新员工"""
      return [False] * len(staff_ids)  # 默认为 False，实际应从 OrgStaff 判断

  def _determine_new_status_list(self, staff_ids: list[int]) -> list[bool]:
      """判断人员是否为新员工"""
      return [False] * len(staff_ids)
  ```

- [ ] **Step 2: 添加 _determine_new_status 方法的真实实现**

  需要从 `OrgStaff` 表判断新员工身份。假设入职时间 < 6 个月为新人：

  ```python
  async def _determine_new_status_batch(self, staff_ids: list[int]) -> dict[int, bool]:
      """批量判断人员是否为新员工"""
      if not staff_ids:
          return {}

      staff_list = list((await self.db.execute(
          select(OrgStaff).where(OrgStaff.id.in_(staff_ids))
      )).scalars().all()))

      from datetime import timedelta
      cutoff_date = date.today() - timedelta(days=180)
      result = {}
      for s in staff_list:
          is_new = False
          if hasattr(s, 'created_at') and s.created_at:
              created = s.created_at.date() if hasattr(s.created_at, 'date') else s.created_at
              is_new = created >= cutoff_date
          elif s.tags and "新员工" in (s.tags or []):
              is_new = True
          result[s.id] = is_new
      return result
  ```

- [ ] **Step 3: 验证模块导入**

  ```bash
  cd backend && python -c "from app.engine.pairing_manager import PairingManager; print('OK')"
  ```

---

### Task 0.3: 集成手动调整后的配对关系更新

**Files:**
- Modify: `backend/app/services/schedule_service.py`

**背景:** 手动调整排班后，需要检查是否影响了配对关系，如果是则更新 `sch_pairing` 表。

- [ ] **Step 1: 找到手动调整的入口方法**

  在 `schedule_service.py` 中找到 `update_schedule` 或类似的手动调整方法。查看它在哪里修改 `SchScheduleDetail` 记录。

- [ ] **Step 2: 在手动调整后调用配对关系更新**

  在手动调整排班明细后，添加配对关系检查：

  ```python
  # 在手动调整方法末尾添加
  if pairing_mgr and schedule_detail_changed:
      # 重新推导该班次的配对关系
      shift_id = schedule.shift_id
      new_pairings = await pairing_mgr.derive_from_schedule(
          shift_id=shift_id,
          month_start=start_of_month,
          month_end=end_of_month,
      )
      if new_pairings:
          await pairing_mgr.save_pairings(shift_id, new_pairings)
  ```

- [ ] **Step 3: 验证**

  手动调整一个排班，检查 `sch_pairing` 表是否正确更新。

---

### Task 0.4: 编写配对关系单元测试

**Files:**
- Modify: `backend/tests/test_pairing.py`

- [ ] **Step 1: 添加 derive_from_schedule 测试**

  ```python
  @pytest.mark.asyncio
  async def test_derive_from_schedule_finds_stable_pairs():
      """测试从排班记录推导配对关系"""
      db = AsyncMock()
      # Mock 排班记录
      mock_schedule = MagicMock()
      mock_schedule.id = 1
      mock_schedule.date = date(2026, 6, 1)
      mock_schedule.shift_id = 10

      mock_detail = MagicMock()
      mock_detail.schedule_id = 1
      mock_detail.staff_id = 100  # 员工A
      # ... 更多 mock

      # 验证推导结果包含稳定的2人组
  ```

- [ ] **Step 2: 添加跨月轮换测试**

  ```python
  def test_special_rotation_across_shifts():
      """测试特殊人员跨班次轮换"""
      # 月A: 白班特殊=[罗士发], 行政特殊=[冯绍晏]
      # 月B: 白班特殊=[冯绍晏], 行政特殊=[罗士发]
      # 验证轮换逻辑正确
  ```

- [ ] **Step 3: 运行测试**

  ```bash
  cd backend && python -m pytest tests/test_pairing.py -v
  ```

---

### Task 0.5: 编写跨月一致性测试

**Files:**
- Create: `backend/tests/test_cross_month_consistency.py`

- [ ] **Step 1: 逐月 vs 多月生成一致性测试**

  ```python
  def test_monthly_vs_multi_month_consistency():
      """逐月生成和多月生成结果应一致"""
      # 设置测试数据：12人，2个特殊人员，3个班次模板
      # 逐月生成 4 个月
      # 多月一次生成 4 个月
      # 对比结果
  ```

- [ ] **Step 2: 手动调整继承测试**

  ```python
  def test_manual_adjustment_propagates():
      """手动调整后自动生成应继承调整结果"""
      # 生成 6 月排班
      # 手动调整 6 月某个配对
      # 生成 7 月排班
      # 验证 7 月使用了调整后的配对
  ```

- [ ] **Step 3: 运行测试**

  ```bash
  cd backend && python -m pytest tests/test_cross_month_consistency.py -v
  ```

---

## Phase 1: Bug 修复验证

### Task 1.1: 验证 publish 方法名修复

**Files:**
- Check: `backend/app/services/auto_schedule_job.py:91`

- [ ] **Step 1: 确认调用正确**

  验证 `auto_schedule_job.py` 第 91 行使用的是 `ScheduleService.publish()` 而非 `publish_schedules()`。当前代码已正确使用。

- [ ] **Step 2: 添加回归测试**

  ```python
  def test_auto_schedule_uses_correct_publish_method():
      """验证自动排班使用正确的 publish 方法名"""
      # Mock ScheduleService.publish 并调用 auto_schedule
      # 确认 publish 被正确调用
  ```

### Task 1.2: 验证跨月连续天数计算

**Files:**
- Check: `backend/app/engine/scheduler.py:158-184`

- [ ] **Step 1: 确认 pre_history 正确传入**

  验证 `schedule_service.py` 第 947-973 行的 pre_history 加载逻辑是否正确。当前实现加载上月最后 `MAX_CONTINUOUS_DAYS` 天的数据，传入 `AutoScheduler`。

- [ ] **Step 2: 确认 `_will_exceed_continuous` 正确使用 pre_history**

  查看 `scheduler.py` 第 158-184 行，确认它合并了 `_pre_history` 和当前排班数据进行连续天数计算。

- [ ] **Step 3: 添加测试**

  ```python
  def test_continuous_days_cross_month():
      """测试跨月连续工作天数计算"""
      # 上月最后 4 天工作 + 本月第 1 天 = 连续 5 天
      # 验证不会在本月第 1 天再次分配
  ```

### Task 1.3: 验证 Swap 清理逻辑

**Files:**
- Check: `backend/app/services/schedule_service.py:1233-1269`

- [ ] **Step 1: 确认只删除 completed/cancelled 的 Swap**

  当前代码（第 1253-1257 行）只删除状态为 `completed` 或 `cancelled` 的 swap 请求。进行中（pending/approved）的 swap 不会被删除，只会将其 `target_schedule_id` 置空（第 1261-1265 行）。

- [ ] **Step 2: 添加测试**

  ```python
  def test_cleanup_preserves_pending_swaps():
      """验证清理排班时保留进行中的调班申请"""
      # 创建一个 pending 状态的 swap 请求
      # 执行 auto_generate（会触发 cleanup）
      # 验证 swap 请求仍然存在
  ```

---

## Phase 2: 槽位绑定泛化验证

### Task 2.1: 验证 SlotGrouper 动态分组

**Files:**
- Check: `backend/app/engine/scheduler.py:215-383`

- [ ] **Step 1: 确认支持 N=10~14 动态分组**

  当前 `SlotGrouper._build_groups` 方法（第 332-383 行）已经支持动态分组：
  - 按新老配对
  - 均匀分配到 3 个槽位
  - 每槽分为 day_group 和 night_group

- [ ] **Step 2: 验证跨月替换逻辑**

  `SlotGrouper._apply_cross_month_replacement` 方法（第 288-330 行）处理人员变更时的槽位继承。确认：
  - 1:1 替换正确
  - 人数不匹配时的处理正确
  - 未分配的新人添加到人数最少的槽位

- [ ] **Step 3: 添加测试**

  ```python
  def test_slot_grouper_dynamic_n():
      """测试不同人数下的槽位分组"""
      # N=10: 每槽 4/3/3
      # N=11: 每槽 4/4/3
      # N=12: 每槽 4/4/4
      # N=13: 每槽 5/4/4
      # N=14: 每槽 5/5/4
  ```

---

## Phase 3: 约束规则验证

### Task 3.1: 验证 HOLIDAY_MODE 约束

**Files:**
- Check: `backend/app/engine/constraint_checker.py:654-721`

- [ ] **Step 1: 确认 _get_holiday_set 函数存在**

  查看 `schedule_service.py` 中是否有 `_get_holiday_set` 函数。如果没有，需要添加或从其他数据源获取节假日。

- [ ] **Step 2: 验证两种模式的实现**

  - `mode: "increase"`: 节假日排班人数不少于 `normal_count + extra_count`
  - `mode: "fixed"`: 节假日必须包含指定的 `staff_ids`

- [ ] **Step 3: 添加测试**

  ```python
  def test_holiday_mode_increase():
      """测试节假日增加排班人数模式"""
      # 设置节假日，验证人数不足时报 warning
  ```

### Task 3.2: 验证 WEEKEND_DIFF 约束

**Files:**
- Check: `backend/app/engine/constraint_checker.py:723-814`

- [ ] **Step 1: 确认两种模式的实现**

  - `mode: "reduced"`: 周末排班人数不超过 `weekday_count - reduced_count`
  - `mode: "different_shift"`: 周末只允许使用指定的 `weekend_shift_ids`

- [ ] **Step 2: 添加测试**

  ```python
  def test_weekend_diff_different_shift():
      """测试周末差异化班次模式"""
      # 设置周末使用非允许的班次，验证报错
  ```

---

## Phase 4: 清理与可配置化验证

### Task 4.1: 清理死代码

**Files:**
- Check: `backend/app/engine/scheduler.py`

- [ ] **Step 1: 查找未调用的方法**

  搜索 `_tier_rotate_select` 是否还存在。如果存在且未被调用，删除它。

- [ ] **Step 2: 清理无用日志**

  查找 `[诊断]` 前缀的日志，确认它们是用于调试的可删除日志。

### Task 4.2: 验证 FairnessScorer 权重可配置化

**Files:**
- Check: `backend/app/engine/scoring.py:21-39`

- [ ] **Step 1: 确认权重从外部传入**

  当前 `FairnessScorer.__init__` 接受 `weights` 参数，默认值为 `None`，使用硬编码默认值。

- [ ] **Step 2: 确认 AutoScheduler 正确传入权重**

  查看 `scheduler.py` 第 1137-1141 行，确认它从 `constraint_params` 中读取 `FAIRNESS_WEIGHTS` 并传入 `FairnessScorer`。

- [ ] **Step 3: 添加测试**

  ```python
  def test_custom_weights_applied():
      """测试自定义权重生效"""
      custom_weights = {"weight_night": 5.0}
      scorer = FairnessScorer(..., weights=custom_weights)
      assert scorer._WEIGHT_NIGHT == 5.0
  ```

---

## 提交消息约定

每个 Task 完成后提交，commit message 格式：

```
phase 0: [具体改动]
phase 1: [具体改动]
phase 2: [具体改动]
phase 3: [具体改动]
phase 4: [具体改动]
```

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
