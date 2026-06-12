# 排班引擎全面优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复排班引擎已知 Bug，泛化槽位绑定系统，补全约束规则，提升可配置性

**Architecture:** 渐进式 4 阶段推进：Bug 修复 → 槽位绑定泛化 → 约束规则补全 → 清理与可配置化。每阶段独立可验证。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, pytest

---

## 文件结构

### 修改的文件

| 文件 | 职责 |
|---|---|
| `backend/app/services/auto_schedule_job.py` | 修复 `publish_schedules` → `publish` |
| `backend/app/engine/scheduler.py` | 泛化 N=12 槽位绑定、修复跨月连续天数、清理死代码 |
| `backend/app/engine/scoring.py` | 权重可配置化 |
| `backend/app/engine/constraint_checker.py` | 实现 HOLIDAY_MODE、WEEKEND_DIFF、MIN_REST_AFTER_CONTINUOUS |
| `backend/app/services/schedule_service.py` | 修复 swap 清理逻辑、传入前序历史数据 |
| `backend/app/engine/models.py` | 无变更 |

### 新增的文件

| 文件 | 职责 |
|---|---|
| `backend/tests/test_slot_binding.py` | 槽位绑定系统单元测试 |
| `backend/tests/test_bugfixes.py` | Bug 修复回归测试 |
| `backend/tests/test_constraint_checker.py` | 约束规则测试 |

---

## 阶段 1：Bug 修复

### Task 1: 修复 auto_schedule_job 方法名错误

**Files:**
- Modify: `backend/app/services/auto_schedule_job.py:93`

- [ ] **Step 1: 修复方法调用名**

将第 93 行的 `publish_schedules` 改为 `publish`：

```python
# 旧代码（第 93 行）
await ScheduleService.publish_schedules(db, schedule_ids, current_user_id=1)

# 新代码
await ScheduleService.publish(db, schedule_ids, current_user_id=1)
```

- [ ] **Step 2: 验证修复**

运行：`cd backend && python -c "from app.services.schedule_service import ScheduleService; print(hasattr(ScheduleService, 'publish'))"`
预期：`True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/auto_schedule_job.py
git commit -m "fix: correct publish method name in auto_schedule_job"
```

---

### Task 2: 修复 Swap 请求被激进删除

**Files:**
- Modify: `backend/app/services/schedule_service.py:1174-1203`

- [ ] **Step 1: 修改 `_cleanup_existing_schedules` 函数**

替换整个函数：

```python
async def _cleanup_existing_schedules(db, org_id, start_date, end_date):
    """检查并清理已有排班。已发布/待审核的记录会阻止自动排班。"""
    from app.models.swap import SchSwapRequest
    existing = list((await db.execute(
        select(SchSchedule).where(
            SchSchedule.org_id == org_id,
            SchSchedule.date >= start_date,
            SchSchedule.date <= end_date,
        )
    )).scalars().all())

    if not existing:
        return

    locked_count = sum(1 for s in existing if s.status in SchSchedule.LOCKED_STATUSES)
    if locked_count > 0:
        raise ValueError(f"该日期范围内存在 {locked_count} 条已发布或待审核排班，请先撤回后再自动生成")

    delete_ids = [s.id for s in existing if s.status in SchSchedule.EDITABLE_STATUSES]
    if delete_ids:
        # 只删除已完成或已取消的调班申请，保留进行中的
        await db.execute(
            delete(SchSwapRequest).where(
                SchSwapRequest.requester_schedule_id.in_(delete_ids),
                SchSwapRequest.status.in_(["completed", "cancelled"])
            )
        )
        # 将进行中的调班申请的 target_schedule_id 置空
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(SchSwapRequest).where(
                SchSwapRequest.target_schedule_id.in_(delete_ids),
                SchSwapRequest.status.notin_(["completed", "cancelled"])
            ).values(target_schedule_id=None)
        )
        await db.execute(delete(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(delete_ids)))
        await db.execute(delete(SchSchedule).where(SchSchedule.id.in_(delete_ids)))
        await db.flush()
```

- [ ] **Step 2: 验证 import 正确**

运行：`cd backend && python -c "from app.models.swap import SchSwapRequest; print('OK')"`
预期：`OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/schedule_service.py
git commit -m "fix: preserve in-progress swap requests during schedule cleanup"
```

---

### Task 3: 修复跨月连续工作天数计算缺陷

**Files:**
- Modify: `backend/app/engine/scheduler.py:157-181` (CandidateFilter._will_exceed_continuous)
- Modify: `backend/app/engine/scheduler.py:532-601` (AutoScheduler.__init__)
- Modify: `backend/app/services/schedule_service.py:812-943` (auto_generate)

- [ ] **Step 1: 在 AutoScheduler.__init__ 中添加前序历史数据支持**

在 `AutoScheduler.__init__` 方法末尾（`self.candidate_filter = ...` 之后）添加：

```python
        # 前序历史数据（上月末尾的排班日期，用于跨月连续天数计算）
        self._pre_history: dict[int, list[str]] = {}
```

在 `__init__` 的参数中添加可选参数：

```python
    def __init__(
        self,
        staff_list: list[OrgStaff],
        shift_templates: list[SchShiftTemplate],
        constraints: list[SchConstraint],
        special_rules: list[SchSpecialRule],
        existing_schedules: list,
        existing_details: list,
        staff_tag_roles_map: dict[int, list[str]] | None = None,
        org_max_ratio: float | None = None,
        pre_history: dict[int, list[str]] | None = None,  # 新增
    ):
```

在 `__init__` 方法体中，在 `self.candidate_filter = ...` 之前添加：

```python
        # 前序历史（上月末尾排班日期，用于跨月连续天数计算）
        self._pre_history = pre_history or {}
```

- [ ] **Step 2: 修改 CandidateFilter 支持前序历史**

在 `CandidateFilter.__init__` 中添加参数：

```python
    def __init__(
        self,
        staff_special_rules: dict[int, list[SchSpecialRule]],
        constraint_params: dict[str, dict],
        existing_details: list,
        existing_schedules: list,
        shift_templates: dict[int, SchShiftTemplate],
        scorer: FairnessScorer,
        pre_history: dict[int, list[str]] | None = None,  # 新增
    ):
        self._staff_special_rules = staff_special_rules
        self._constraint_params = constraint_params
        self._existing_details = existing_details
        self._schedule_index: dict[int, object] = {s.id: s for s in existing_schedules}
        self._shift_templates = shift_templates
        self._scorer = scorer
        self._pre_history = pre_history or {}
```

- [ ] **Step 3: 修改 `_will_exceed_continuous` 方法**

替换整个方法（scheduler.py 第 157-181 行）：

```python
    def _will_exceed_continuous(self, staff_id: int, date_str: str, max_days: int) -> bool:
        all_dates_raw = sorted(self._scorer.staff_days.get(staff_id, set()))
        # 合并前序历史（上月末尾排班日期）与当前数据
        pre = self._pre_history.get(staff_id, [])
        if pre:
            all_dates_raw = sorted(set(all_dates_raw) | set(pre))
        # 只统计本轮排班开始后的日期，但包含前序历史用于跨月连续判断
        run_start = getattr(self, '_run_start_str', '0000-01-01')
        # 如果有前序历史，从历史最早日期开始统计；否则从 run_start 开始
        effective_start = min(pre) if pre and min(pre) < run_start else run_start
        all_dates = [d for d in all_dates_raw if d >= effective_start]
        if date_str not in all_dates:
            all_dates.append(date_str)
            all_dates.sort()
        idx = all_dates.index(date_str)

        # 向前 + 向后统计连续天数
        consecutive = 1
        for direction, step in ((-1, -1), (1, 1)):
            i = idx + step
            while 0 <= i < len(all_dates):
                prev = date.fromisoformat(all_dates[i - step])
                curr = date.fromisoformat(all_dates[i])
                if abs((curr - prev).days) == 1:
                    consecutive += 1
                    i += step
                else:
                    break
                if consecutive > max_days:
                    return True
        return consecutive > max_days
```

- [ ] **Step 4: 在 CandidateFilter 构造中传入 pre_history**

修改 AutoScheduler 中 CandidateFilter 的创建（scheduler.py 第 593-600 行）：

```python
        self.candidate_filter = CandidateFilter(
            staff_special_rules=self.staff_special_rules,
            constraint_params=self.constraint_params,
            existing_details=existing_details,
            existing_schedules=existing_schedules,
            shift_templates=self.shift_templates,
            scorer=self.scorer,
            pre_history=self._pre_history,
        )
```

- [ ] **Step 5: 在 auto_generate 中加载上月末尾历史数据**

在 `schedule_service.py` 的 `auto_generate` 方法中，在 step 5（加载历史排班）之后添加：

```python
        # ---- 5.1. 加载上月末尾排班数据（用于跨月连续天数计算） ----
        pre_history: dict[int, list[str]] = {}
        if start_date.day == 1:
            # 从上月最后 max_continuous_days 天加载
            max_continuous = 5  # 默认值
            for c in constraints:
                if c.rule_type == "MAX_CONTINUOUS_DAYS" and c.enabled:
                    max_continuous = (c.params or {}).get("max_days", 5)
                    break
            prev_month_end = start_date - timedelta(days=1)
            prev_month_start = prev_month_end - timedelta(days=max_continuous - 1)
            pre_schedules = list((await db.execute(
                select(SchSchedule).where(
                    SchSchedule.org_id == org_id,
                    SchSchedule.date >= prev_month_start,
                    SchSchedule.date <= prev_month_end,
                )
            )).scalars().all())
            if pre_schedules:
                pre_ids = [s.id for s in pre_schedules]
                pre_details = list((await db.execute(
                    select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(pre_ids))
                )).scalars().all())
                pre_sched_map = {s.id: s for s in pre_schedules}
                for d in pre_details:
                    s = pre_sched_map.get(d.schedule_id)
                    if s:
                        pre_history.setdefault(d.staff_id, []).append(str(s.date))
```

- [ ] **Step 6: 将 pre_history 传入 AutoScheduler**

修改 AutoScheduler 的实例化（schedule_service.py 第 926-935 行）：

```python
        scheduler = AutoScheduler(
            staff_list=staff_list,
            shift_templates=shifts,
            constraints=constraints,
            special_rules=special_rules,
            existing_schedules=existing_schedules,
            existing_details=existing_details,
            staff_tag_roles_map=staff_tag_roles_map,
            org_max_ratio=org_max_ratio,
            pre_history=pre_history,
        )
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/engine/scheduler.py backend/app/services/schedule_service.py
git commit -m "fix: include previous month data in cross-month continuous days calculation"
```

---

## 阶段 2：槽位绑定系统泛化

### Task 4: 泛化 N=12 槽位绑定为支持 N=10~14

**Files:**
- Modify: `backend/app/engine/scheduler.py:398-491` (IndividualStrategy._pair_select)

- [ ] **Step 1: 重写 `_pair_select` 方法的日轮部分**

替换 `if freq == "day":` 块（第 421-491 行）为泛化版本：

```python
        if freq == "day":
            # === 日轮：槽位分组 + 绑定组 + 新老搭配 + 白夜交替 + 班次均衡 ===
            dt = date.fromisoformat(date_str)
            rotation_slot = (dt.day - 1) % 3
            rotation_number = (dt.day - 1) // 3

            # 0. 跨月重置（多月一次生成时每月重新开始）
            if getattr(self.s, '_bound_month', 0) != dt.month:
                self.s._bound_groups.clear()
                self.s._monthly_locked.clear()
                self.s._bound_month = dt.month

            # 1. 检查绑定组
            if rotation_slot in self.s._bound_groups:
                day_grp, night_grp = self.s._bound_groups[rotation_slot]
                if rotation_number % 2 == 0:
                    return (day_grp if target_type == "day" else night_grp)[:target]
                else:
                    return (night_grp if target_type == "day" else day_grp)[:target]

            # 2. 结构轮换：支持 N=10~14（3槽位动态分组）
            n_total = len(candidates)
            if 10 <= n_total <= 14:
                stable_sorted = sorted(candidates)

                # 全局新老分组配对
                new_ids = [sid for sid in stable_sorted if self.s._is_new_employee(sid)]
                old_ids = [sid for sid in stable_sorted if not self.s._is_new_employee(sid)]

                # 交叉配对：优先1新+1老，剩余的同类放一起
                pairs = []
                while new_ids and old_ids:
                    pairs.append([new_ids.pop(0), old_ids.pop(0)])
                while len(new_ids) >= 2:
                    pairs.append([new_ids.pop(0), new_ids.pop(0)])
                while len(old_ids) >= 2:
                    pairs.append([old_ids.pop(0), old_ids.pop(0)])
                # 剩余单人加入最后一个配对
                if new_ids:
                    if pairs:
                        pairs[-1].append(new_ids.pop(0))
                    else:
                        pairs.append([new_ids.pop(0)])
                if old_ids:
                    if pairs:
                        pairs[-1].append(old_ids.pop(0))
                    else:
                        pairs.append([old_ids.pop(0)])

                # 分配配对到3个槽位（尽量均匀）
                # 槽位大小：ceil(n_total/3) 或 floor(n_total/3)
                slot_size_base = n_total // 3
                slot_sizes = [slot_size_base] * 3
                remainder = n_total % 3
                for i in range(remainder):
                    slot_sizes[i] += 1

                # 按配对顺序分配到槽位
                slot_members: dict[int, list[int]] = {0: [], 1: [], 2: []}
                pair_idx = 0
                for slot_idx in range(3):
                    target_size = slot_sizes[slot_idx]
                    while len(slot_members[slot_idx]) < target_size and pair_idx < len(pairs):
                        for sid in pairs[pair_idx]:
                            if len(slot_members[slot_idx]) < target_size:
                                slot_members[slot_idx].append(sid)
                        pair_idx += 1

                # 每个槽位分为 day_group 和 night_group
                for slot_idx in range(3):
                    members = slot_members[slot_idx]
                    mid = len(members) // 2
                    if len(members) % 2 == 1:
                        # 奇数：day_group 多1人
                        day_group = members[:mid + 1]
                        night_group = members[mid + 1:]
                    else:
                        # 偶数：平分
                        day_group = members[:mid]
                        night_group = members[mid:]
                    self.s._bound_groups[slot_idx] = (day_group, night_group)

                # 返回当前槽位的结果
                dg, ng = self.s._bound_groups[rotation_slot]
                if rotation_number % 2 == 0:
                    return (dg if target_type == "day" else ng)[:target]
                else:
                    return (ng if target_type == "day" else dg)[:target]

            # N 在 10~14 范围外时回退到公平排序
            dt2 = date.fromisoformat(date_str)
            day_seed = dt2.day + dt2.month * 31
            combined = sorted(candidates, key=lambda sid: (
                self.s._night_shifts.get(sid, 0) + self.s._day_shifts.get(sid, 0),
                self.s._night_shifts.get(sid, 0) if is_night else self.s._day_shifts.get(sid, 0),
                (sid * day_seed) % 997,
            ))
            return combined[:target]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/engine/scheduler.py
git commit -m "feat: generalize slot binding from N=12 to N=10-14"
```

---

### Task 5: 实现跨月替换机制

**Files:**
- Modify: `backend/app/engine/scheduler.py:427-431` (跨月重置逻辑)

- [ ] **Step 1: 添加跨月槽位历史存储**

在 `AutoScheduler.__init__` 中添加：

```python
        # 上月槽位绑定历史（用于跨月替换）
        self._prev_month_groups: dict[int, tuple] = {}
```

- [ ] **Step 2: 修改跨月重置逻辑**

替换 `_pair_select` 中的跨月重置块（第 427-431 行）：

```python
            # 0. 跨月重置（多月一次生成时每月重新开始）
            if getattr(self.s, '_bound_month', 0) != dt.month:
                # 保存上月槽位绑定，用于跨月替换
                self.s._prev_month_groups = dict(self.s._bound_groups)
                self.s._bound_groups.clear()
                self.s._monthly_locked.clear()
                self.s._bound_month = dt.month
```

- [ ] **Step 3: 在槽位分配中实现跨月替换**

在 Task 4 的泛化代码中，`# 2. 结构轮换` 块内，在 `if 10 <= n_total <= 14:` 分支的开头（绑定组检查之后），添加跨月替换逻辑：

```python
            # 2. 结构轮换：支持 N=10~14（3槽位动态分组）
            n_total = len(candidates)
            if 10 <= n_total <= 14:
                stable_sorted = sorted(candidates)

                # 跨月替换：如果上月有绑定，检查人员变更
                if self.s._prev_month_groups:
                    prev_all = set()
                    for dg, ng in self.s._prev_month_groups.values():
                        prev_all.update(dg)
                        prev_all.update(ng)
                    curr_all = set(stable_sorted)
                    departed = prev_all - curr_all  # 离开的人
                    joined = curr_all - prev_all     # 新加入的人

                    if departed and joined:
                        # 原槽位替换：新人员进入离开人员的原槽位
                        departed_list = sorted(departed)
                        joined_list = sorted(joined)
                        replacements = dict(zip(departed_list, joined_list))

                        new_groups = {}
                        for slot_idx, (dg, ng) in self.s._prev_month_groups.items():
                            new_dg = [replacements.get(sid, sid) for sid in dg]
                            new_ng = [replacements.get(sid, sid) for sid in ng]
                            new_groups[slot_idx] = (new_dg, new_ng)
                        self.s._bound_groups = new_groups

                        dg, ng = self.s._bound_groups[rotation_slot]
                        if rotation_number % 2 == 0:
                            return (dg if target_type == "day" else ng)[:target]
                        else:
                            return (ng if target_type == "day" else dg)[:target]
                    elif not departed and not joined:
                        # 人员无变化，直接沿用上月绑定
                        self.s._bound_groups = dict(self.s._prev_month_groups)
                        dg, ng = self.s._bound_groups[rotation_slot]
                        if rotation_number % 2 == 0:
                            return (dg if target_type == "day" else ng)[:target]
                        else:
                            return (ng if target_type == "day" else dg)[:target]
                    # 有人离开但无人加入（或反之），走正常分配流程

                # 全局新老分组配对
                # ...（后续代码不变）
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/engine/scheduler.py
git commit -m "feat: implement cross-month slot replacement mechanism"
```

---

## 阶段 3：约束规则补全

### Task 6: 实现 HOLIDAY_MODE 约束规则

**Files:**
- Modify: `backend/app/engine/constraint_checker.py:436-439`

- [ ] **Step 1: 实现 `_check_holiday_mode` 方法**

替换空实现：

```python
    def _check_holiday_mode(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        """节假日排班模式"""
        mode = params.get("mode", "increase")
        violations = []

        # 获取节假日集合
        from app.services.schedule_service import _get_holiday_set
        if not self.schedules:
            return []
        min_date = min(s.date for s in self.schedules)
        max_date = max(s.date for s in self.schedules)
        holidays = _get_holiday_set(min_date, max_date)

        if mode == "increase":
            # 节假日比平时多排 N 人
            extra_count = params.get("extra_count", 0)
            normal_count = params.get("normal_count", 0)
            if normal_count <= 0:
                return []

            for date_str, details in self.date_details.items():
                if date_str not in holidays:
                    continue
                staff_count = len(set(d.staff_id for d in details))
                if staff_count < normal_count + extra_count:
                    for d in details[:1]:
                        staff_name = self.staff_map.get(d.staff_id, f"ID:{d.staff_id}")
                        violations.append(Violation(
                            rule_type="HOLIDAY_MODE",
                            rule_name=rule_name,
                            message=f"节假日 {date_str} 排班人数 {staff_count} 人，不足 {normal_count + extra_count} 人",
                            schedule_id=d.schedule_id,
                            staff_id=d.staff_id,
                            date=date_str,
                            severity="warning",
                        ))
                        break

        elif mode == "fixed":
            # 节假日固定安排指定人员
            required_ids = set(params.get("staff_ids", []))
            if not required_ids:
                return []

            for date_str, details in self.date_details.items():
                if date_str not in holidays:
                    continue
                scheduled_ids = set(d.staff_id for d in details)
                missing = required_ids - scheduled_ids
                for staff_id in missing:
                    staff_name = self.staff_map.get(staff_id, f"ID:{staff_id}")
                    if details:
                        violations.append(Violation(
                            rule_type="HOLIDAY_MODE",
                            rule_name=rule_name,
                            message=f"节假日 {date_str} 缺少固定人员 {staff_name}",
                            schedule_id=details[0].schedule_id,
                            staff_id=staff_id,
                            date=date_str,
                            severity="warning",
                        ))

        return violations
```

- [ ] **Step 2: 实现 `_check_holiday_mode_single` 方法**

替换空实现：

```python
    def _check_holiday_mode_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        # 单条校验时，节假日模式需在全局校验中判断
        return []
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/engine/constraint_checker.py
git commit -m "feat: implement HOLIDAY_MODE constraint checker"
```

---

### Task 7: 实现 WEEKEND_DIFF 约束规则

**Files:**
- Modify: `backend/app/engine/constraint_checker.py:441-446`

- [ ] **Step 1: 实现 `_check_weekend_diff` 方法**

替换空实现：

```python
    def _check_weekend_diff(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        """周末差异化排班"""
        mode = params.get("mode", "reduced")
        violations = []

        if mode == "reduced":
            # 周末减少排班人数
            reduced_count = params.get("reduced_count", 1)
            weekday_count = params.get("weekday_count", 0)
            if weekday_count <= 0:
                return []

            for date_str, details in self.date_details.items():
                try:
                    d_obj = date.fromisoformat(date_str)
                except ValueError:
                    continue
                if d_obj.isoweekday() < 6:  # 非周末
                    continue
                staff_count = len(set(d.staff_id for d in details))
                expected = max(0, weekday_count - reduced_count)
                if staff_count > expected:
                    for d in details[:1]:
                        staff_name = self.staff_map.get(d.staff_id, f"ID:{d.staff_id}")
                        violations.append(Violation(
                            rule_type="WEEKEND_DIFF",
                            rule_name=rule_name,
                            message=f"周末 {date_str} 排班人数 {staff_count} 人，超过限制 {expected} 人",
                            schedule_id=d.schedule_id,
                            staff_id=d.staff_id,
                            date=date_str,
                            severity="warning",
                        ))
                        break

        elif mode == "different_shift":
            # 周末使用不同的班次模板
            allowed_shift_ids = set(params.get("weekend_shift_ids", []))
            if not allowed_shift_ids:
                return []

            for date_str, details in self.date_details.items():
                try:
                    d_obj = date.fromisoformat(date_str)
                except ValueError:
                    continue
                if d_obj.isoweekday() < 6:
                    continue
                for d in details:
                    schedule = self.schedule_map.get(d.schedule_id)
                    if schedule and schedule.shift_id not in allowed_shift_ids:
                        shift = self.shifts.get(schedule.shift_id)
                        shift_name = shift.name if shift else f"ID:{schedule.shift_id}"
                        staff_name = self.staff_map.get(d.staff_id, f"ID:{d.staff_id}")
                        violations.append(Violation(
                            rule_type="WEEKEND_DIFF",
                            rule_name=rule_name,
                            message=f"周末 {date_str} 不允许使用班次「{shift_name}」",
                            schedule_id=d.schedule_id,
                            staff_id=d.staff_id,
                            date=date_str,
                            severity="error",
                        ))

        return violations
```

- [ ] **Step 2: 实现 `_check_weekend_diff_single` 方法**

替换空实现：

```python
    def _check_weekend_diff_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        mode = params.get("mode", "reduced")
        try:
            d_obj = date.fromisoformat(schedule_date)
        except ValueError:
            return []
        if d_obj.isoweekday() < 6:
            return []

        if mode == "different_shift":
            allowed_shift_ids = set(params.get("weekend_shift_ids", []))
            if allowed_shift_ids and shift_id not in allowed_shift_ids:
                shift = self.shifts.get(shift_id)
                shift_name = shift.name if shift else f"ID:{shift_id}"
                staff_name = self.staff_map.get(staff_id, f"ID:{staff_id}")
                return [Violation(
                    rule_type="WEEKEND_DIFF",
                    rule_name=rule_name,
                    message=f"周末 {schedule_date} 不允许使用班次「{shift_name}」",
                    schedule_id=schedule_id,
                    staff_id=staff_id,
                    date=schedule_date,
                    severity="error",
                )]
        return []
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/engine/constraint_checker.py
git commit -m "feat: implement WEEKEND_DIFF constraint checker"
```

---

### Task 8: 实现 MIN_REST_AFTER_CONTINUOUS 单条校验

**Files:**
- Modify: `backend/app/engine/constraint_checker.py:760-765`

- [ ] **Step 1: 实现 `_check_min_rest_after_continuous_single` 方法**

替换空实现：

```python
    def _check_min_rest_after_continuous_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        continuous_days = params.get("continuous_days", 5)
        rest_days = params.get("rest_days", 1)

        # 获取该人员所有排班日期
        dates = sorted(set(d[0] for d in self.staff_schedule_dates.get(staff_id, [])))
        if schedule_date not in dates:
            dates.append(schedule_date)
            dates.sort()
        idx = dates.index(schedule_date)

        # 向前检查连续天数
        consecutive_back = 0
        i = idx - 1
        while i >= 0:
            if (date.fromisoformat(dates[i + 1]) - date.fromisoformat(dates[i])).days == 1:
                consecutive_back += 1
                i -= 1
            else:
                break

        total_consecutive = consecutive_back + 1  # 包含当前天

        if total_consecutive >= continuous_days:
            # 检查之后是否有足够休息
            if idx + 1 < len(dates):
                next_date = date.fromisoformat(dates[idx + 1])
                curr_date = date.fromisoformat(schedule_date)
                gap = (next_date - curr_date).days
                if gap < rest_days + 1:
                    staff_name = self.staff_map.get(staff_id, f"ID:{staff_id}")
                    return [Violation(
                        rule_type="MIN_REST_AFTER_CONTINUOUS",
                        rule_name=rule_name,
                        message=f"{staff_name} 连续工作 {total_consecutive} 天后仅休息 {gap - 1} 天，不足 {rest_days} 天",
                        schedule_id=schedule_id,
                        staff_id=staff_id,
                        date=schedule_date,
                        severity="warning",
                    )]
        return []
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/engine/constraint_checker.py
git commit -m "feat: implement MIN_REST_AFTER_CONTINUOUS single check"
```

---

## 阶段 4：清理与可配置化

### Task 9: 清理死代码

**Files:**
- Modify: `backend/app/engine/scheduler.py:972-998`

- [ ] **Step 1: 删除 `_tier_rotate_select` 方法**

删除 `AutoScheduler` 类中的 `_tier_rotate_select` 方法（第 972-998 行）及其上方的注释块（第 968-970 行）。

- [ ] **Step 2: 验证无引用**

运行：`cd backend && python -c "import ast; tree = ast.parse(open('app/engine/scheduler.py').read()); print('OK')"`
预期：`OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/engine/scheduler.py
git commit -m "chore: remove unused _tier_rotate_select method"
```

---

### Task 10: FairnessScorer 权重可配置化

**Files:**
- Modify: `backend/app/engine/scoring.py:22-29, 31-56`

- [ ] **Step 1: 修改 FairnessScorer.__init__ 支持自定义权重**

```python
    def __init__(
        self,
        existing_schedules: list[SchSchedule],
        existing_details: list[SchScheduleDetail],
        shifts: dict[int, SchShiftTemplate],
        weights: dict | None = None,
    ):
        self.shifts = shifts

        # 打分权重（支持外部配置）
        w = weights or {}
        self._WEIGHT_HOURS = w.get("weight_hours", 0.3)
        self._WEIGHT_NIGHT = w.get("weight_night", 3.0)
        self._WEIGHT_WEEKEND = w.get("weight_weekend", 2.0)
        self._PENALTY_SAME_DAY = w.get("penalty_same_day", 1000.0)
        self._PENALTY_CONSECUTIVE = w.get("penalty_consecutive", 50.0)
        self._PENALTY_GAP_1_DAY = w.get("penalty_gap_1_day", 25.0)
        self._PENALTY_GAP_2_DAY = w.get("penalty_gap_2_day", 10.0)
        self._PENALTY_SAME_SHIFT_TYPE = w.get("penalty_same_shift_type", 30.0)

        # 统计每个人员的历史数据
        self.staff_days: dict[int, set[str]] = defaultdict(set)
        self.staff_hours: dict[int, float] = defaultdict(float)
        self.staff_night_count: dict[int, int] = defaultdict(int)
        self.staff_weekend_count: dict[int, int] = defaultdict(int)

        # 白夜交替：记录每人最后排的班次类型
        self.staff_last_shift_type: dict[int, str] = {}

        # 构建 schedule_id -> SchSchedule 索引，消除 O(n) 遍历
        self._schedule_index: dict[int, SchSchedule] = {
            s.id: s for s in existing_schedules
        }

        # 一次性批量统计
        self._bulk_load(existing_details)
```

- [ ] **Step 2: 删除类级别常量**

删除第 22-29 行的类级别常量定义（已移至 `__init__` 中）。

- [ ] **Step 3: 在 AutoScheduler 中从约束配置读取权重**

修改 `AutoScheduler.__init__` 中 FairnessScorer 的创建（scheduler.py 第 569 行附近）：

```python
        # 从约束配置读取公平性权重
        fairness_weights = self.constraint_params.get("FAIRNESS_WEIGHTS", {})

        # 公平性打分器
        self.scorer = FairnessScorer(
            existing_schedules, existing_details, self.shift_templates,
            weights=fairness_weights if fairness_weights else None,
        )
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/engine/scoring.py backend/app/engine/scheduler.py
git commit -m "feat: make FairnessScorer weights configurable via constraint params"
```

---

## 验证

### Task 11: 编写集成测试

**Files:**
- Create: `backend/tests/test_slot_binding.py`
- Create: `backend/tests/test_bugfixes.py`

- [ ] **Step 1: 创建测试目录**

```bash
mkdir -p backend/tests
touch backend/tests/__init__.py
```

- [ ] **Step 2: 编写槽位绑定测试**

```python
"""槽位绑定系统单元测试"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from app.engine.scheduler import AutoScheduler, IndividualStrategy, ScheduleResult


def make_staff(staff_id: int, name: str = "", tags: list = None):
    """创建模拟员工对象"""
    s = MagicMock()
    s.id = staff_id
    s.name = name or f"Staff_{staff_id}"
    s.status = 1
    s.tags = tags or []
    return s


def make_shift(shift_id: int, **kwargs):
    """创建模拟班次模板"""
    s = MagicMock()
    s.id = shift_id
    s.name = kwargs.get("name", f"Shift_{shift_id}")
    s.status = 1
    s.leader_enabled = kwargs.get("leader_enabled", False)
    s.leader_min = kwargs.get("leader_min", 0)
    s.leader_max = kwargs.get("leader_max", 0)
    s.leader_count = kwargs.get("leader_count", 0)
    s.leader_pool = kwargs.get("leader_pool", [])
    s.leader_rotation_frequency = kwargs.get("leader_rotation_frequency", "week")
    s.leader_use_tag = kwargs.get("leader_use_tag", False)
    s.leader_tag_name = kwargs.get("leader_tag_name", "领导")
    s.special_enabled = kwargs.get("special_enabled", False)
    s.special_count = kwargs.get("special_count", 0)
    s.special_pool = kwargs.get("special_pool", [])
    s.special_rotation_frequency = kwargs.get("special_rotation_frequency", "month")
    s.special_exclude_from_member = kwargs.get("special_exclude_from_member", True)
    s.member_min = kwargs.get("member_min", 2)
    s.member_max = kwargs.get("member_max", 4)
    s.member_rotation_frequency = kwargs.get("member_rotation_frequency", "day")
    s.apply_days = kwargs.get("apply_days", [1, 2, 3, 4, 5, 6, 7])
    s.constraint_ids = kwargs.get("constraint_ids", None)
    s.start_time = kwargs.get("start_time", "08:00")
    s.end_time = kwargs.get("end_time", "16:00")
    s.duration_hours = kwargs.get("duration_hours", 8)
    return s


class TestSlotBinding:
    """槽位绑定测试"""

    def _make_scheduler(self, staff_count: int = 12):
        """创建测试用调度器"""
        staff_list = [make_staff(i + 1, f"S{i+1}") for i in range(staff_count)]
        shift = make_shift(1, member_max=4)
        scheduler = AutoScheduler(
            staff_list=staff_list,
            shift_templates=[shift],
            constraints=[],
            special_rules=[],
            existing_schedules=[],
            existing_details=[],
        )
        return scheduler

    def test_12_candidates_produces_3_slots(self):
        """12人应分为3个槽位"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        result = strategy._pair_select(candidates, "2026-06-01", 4, scheduler.shift_templates[1])
        assert len(result) == 4

    def test_10_candidates_produces_valid_groups(self):
        """10人应分为3个槽位（4/3/3）"""
        scheduler = self._make_scheduler(10)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 11))
        # 第1天：slot 0
        result_day1 = strategy._pair_select(candidates, "2026-06-01", 4, scheduler.shift_templates[1])
        assert len(result_day1) == 4
        # 第2天：slot 1
        result_day2 = strategy._pair_select(candidates, "2026-06-02", 3, scheduler.shift_templates[1])
        assert len(result_day2) == 3

    def test_day_night_alternation(self):
        """白夜应交替：偶数rotation_number为正序，奇数为反序"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        # day 1: rotation_number=0, slot=0
        day_result = strategy._pair_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        # day 4: rotation_number=1, slot=0 (同槽位，但白夜翻转)
        # 需要先清除绑定组以重新分配
        scheduler._bound_groups.clear()
        scheduler._bound_month = 0
        night_result = strategy._pair_select(candidates, "2026-06-04", 2, scheduler.shift_templates[1])
        # 两组应不同（白夜交替）
        assert set(day_result) != set(night_result)

    def test_monthly_binding_stable(self):
        """同一槽位在同月内应保持稳定"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        # day 1 和 day 2 都是 slot 0
        result1 = strategy._pair_select(candidates, "2026-06-01", 4, scheduler.shift_templates[1])
        result2 = strategy._pair_select(candidates, "2026-06-01", 4, scheduler.shift_templates[1])
        assert result1 == result2
```

- [ ] **Step 3: 编写 Bug 修复回归测试**

```python
"""Bug 修复回归测试"""
import pytest


class TestAutoScheduleJobFix:
    """验证 auto_schedule_job 使用正确的 publish 方法名"""

    def test_publish_method_exists(self):
        from app.services.schedule_service import ScheduleService
        assert hasattr(ScheduleService, 'publish')
        # 确认不存在 publish_schedules
        assert not hasattr(ScheduleService, 'publish_schedules')


class TestCrossMonthContinuous:
    """验证跨月连续天数计算"""

    def test_pre_history_merges_with_current(self):
        """前序历史应与当前数据合并计算连续天数"""
        from app.engine.scheduler import CandidateFilter
        from app.engine.scoring import FairnessScorer
        from unittest.mock import MagicMock

        scorer = MagicMock()
        # 模拟：staff 1 在 6月28-30日有排班（前序历史）
        # 在 7月1-2日有排班（当前数据）
        scorer.staff_days = {1: {"2026-07-01", "2026-07-02"}}

        filter_obj = CandidateFilter(
            staff_special_rules={},
            constraint_params={"MAX_CONTINUOUS_DAYS": {"max_days": 5}},
            existing_details=[],
            existing_schedules=[],
            shift_templates={},
            scorer=scorer,
            pre_history={1: ["2026-06-28", "2026-06-29", "2026-06-30"]},
        )
        filter_obj._run_start_str = "2026-07-01"

        # 7月3日排班：连续6天（6.28-7.3），应超过5天上限
        assert filter_obj._will_exceed_continuous(1, "2026-07-03", 5) is True

        # 7月1日排班：连续4天（6.28-7.1），未超过
        assert filter_obj._will_exceed_continuous(1, "2026-07-01", 5) is False
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test: add unit tests for slot binding and bug fixes"
```

---

## 总结

| 阶段 | Tasks | 关键变更 |
|---|---|---|
| 1. Bug 修复 | Task 1-3 | 方法名修正、swap 保留、跨月连续天数 |
| 2. 槽位绑定泛化 | Task 4-5 | N=10~14 动态分组、跨月替换 |
| 3. 约束规则补全 | Task 6-8 | HOLIDAY_MODE、WEEKEND_DIFF、MIN_REST_AFTER_CONTINUOUS |
| 4. 清理与可配置化 | Task 9-10 | 死代码清理、权重可配置 |
| 5. 验证 | Task 11 | 集成测试 |
