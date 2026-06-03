"""自动排班算法引擎"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from app.engine.scoring import FairnessScorer
from app.models import OrgStaff
from app.models.constraint import SchConstraint
from app.models.shift_template import SchShiftTemplate
from app.models.special_rule import SchSpecialRule


# ====================================================================== #
#  数据结构
# ====================================================================== #

class ScheduleResult:
    """单条排班结果"""

    __slots__ = ("date", "shift_id", "org_id", "leader_ids", "member_ids", "conflicts")

    def __init__(self, date_str: str, shift_id: int, org_id: int):
        self.date = date_str
        self.shift_id = shift_id
        self.org_id = org_id
        self.leader_ids: list[int] = []
        self.member_ids: list[int] = []
        self.conflicts: list[str] = []


# ====================================================================== #
#  候选人过滤链
# ====================================================================== #

class CandidateFilter:
    """统一的候选人过滤链 —— 依次应用特殊规则 + 约束规则。"""

    def __init__(
        self,
        staff_special_rules: dict[int, list[SchSpecialRule]],
        constraint_params: dict[str, dict],
        existing_details: list,
        existing_schedules: list,
        shift_templates: dict[int, SchShiftTemplate],
        scorer: FairnessScorer,
    ):
        self._staff_special_rules = staff_special_rules
        self._constraint_params = constraint_params
        self._existing_details = existing_details
        self._schedule_index: dict[int, object] = {s.id: s for s in existing_schedules}
        self._shift_templates = shift_templates
        self._scorer = scorer

    def apply(
        self,
        candidates: list[int],
        date_str: str,
        shift_id: int,
        exclude_ids: set[int] | None = None,
    ) -> list[int]:
        """依次过特殊规则 → 约束规则，返回通过的候选人。"""
        pool = [sid for sid in candidates if sid not in (exclude_ids or set())]
        pool = self._filter_by_special_rules(pool, date_str, shift_id)
        pool = self._filter_by_constraints(pool, date_str, shift_id)
        return pool

    # ---- 特殊规则 ----

    def _filter_by_special_rules(
        self, candidates: list[int], date_str: str, shift_id: int,
    ) -> list[int]:
        filtered = []
        for sid in candidates:
            if not self._is_excluded_by_special_rules(sid, date_str, shift_id):
                filtered.append(sid)
        return filtered

    def _is_excluded_by_special_rules(
        self, staff_id: int, date_str: str, shift_id: int,
    ) -> bool:
        for rule in self._staff_special_rules.get(staff_id, []):
            # 有效期检查
            if rule.effective_from and date_str < str(rule.effective_from):
                continue
            if rule.effective_to and date_str > str(rule.effective_to):
                continue

            params = rule.params or {}

            if rule.rule_type == "exclude_shift":
                if shift_id in params.get("exclude_shift_ids", []):
                    return True

            elif rule.rule_type == "include_shift":
                included = params.get("include_shift_ids", [])
                if included and shift_id not in included:
                    return True

            elif rule.rule_type == "exclude_date":
                if date_str in params.get("exclude_dates", []):
                    return True

            elif rule.rule_type == "exclude_weekday":
                try:
                    weekday = date.fromisoformat(date_str).isoweekday()
                except ValueError:
                    continue
                if (
                    weekday in params.get("exclude_weekdays", [])
                    and shift_id in params.get("exclude_shift_ids", [])
                ):
                    return True

        return False

    # ---- 约束规则 ----

    def _filter_by_constraints(
        self, candidates: list[int], date_str: str, shift_id: int,
    ) -> list[int]:
        return [sid for sid in candidates if self._passes_constraints(sid, date_str, shift_id)]

    def _passes_constraints(self, staff_id: int, date_str: str, shift_id: int) -> bool:
        # MAX_SHIFTS_PER_DAY
        max_per_day = self._constraint_params.get("MAX_SHIFTS_PER_DAY", {}).get("count", 1)
        if self._count_today(staff_id, date_str) >= max_per_day:
            return False

        # MAX_CONTINUOUS_DAYS
        max_days = self._constraint_params.get("MAX_CONTINUOUS_DAYS", {}).get("max_days", 5)
        if self._will_exceed_continuous(staff_id, date_str, max_days):
            return False

        # MIN_SHIFT_INTERVAL
        min_hours = self._constraint_params.get("MIN_SHIFT_INTERVAL", {}).get("hours", 8)
        if self._interval_violated(staff_id, date_str, shift_id, min_hours):
            return False

        return True

    def _count_today(self, staff_id: int, date_str: str) -> int:
        """该人员当天已排班次数（历史 + 本轮）。"""
        count = 0
        for d in self._existing_details:
            s = self._schedule_index.get(d.schedule_id)
            if s and str(getattr(s, "date", "")) == date_str and d.staff_id == staff_id:
                count += 1
        if date_str in self._scorer.staff_days.get(staff_id, set()):
            count += 1
        return count

    def _will_exceed_continuous(self, staff_id: int, date_str: str, max_days: int) -> bool:
        all_dates_raw = sorted(self._scorer.staff_days.get(staff_id, set()))
        # 只统计本轮排班开始后的日期，避免跨月历史数据串联
        run_start = getattr(self, '_run_start_str', '0000-01-01')
        all_dates = [d for d in all_dates_raw if d >= run_start]
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

    def _interval_violated(
        self, staff_id: int, date_str: str, shift_id: int, min_hours: int,
    ) -> bool:
        shift = self._shift_templates.get(shift_id)
        if not shift:
            return False

        for d in self._existing_details:
            s = self._schedule_index.get(d.schedule_id)
            if not s or str(getattr(s, "date", "")) != date_str or d.staff_id != staff_id:
                continue
            prev_shift = self._shift_templates.get(getattr(s, "shift_id", None))
            if not prev_shift:
                continue
            try:
                peh, pem = map(int, prev_shift.end_time.split(":"))
                csh, csm = map(int, shift.start_time.split(":"))
                gap = ((csh * 60 + csm) - (peh * 60 + pem)) / 60
                if 0 < gap < min_hours:
                    return True
            except (ValueError, AttributeError):
                continue
        return False


# ====================================================================== #
#  排班策略（简化 — 只保留逐人轮询）
# ====================================================================== #

class ScheduleStrategy(ABC):
    """排班策略基类。"""

    def __init__(self, scheduler: AutoScheduler):
        self.s = scheduler  # 持有引擎引用，访问 scorer / filter 等

    @abstractmethod
    def assign(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        result: ScheduleResult,
        include_leader: bool,
    ) -> list[str]:
        """执行排班，返回冲突列表。"""
        ...


class IndividualStrategy(ScheduleStrategy):
    """逐人轮询排班。"""

    def assign(
        self, shift, date_str, available_ids, result,
    ) -> list[str]:
        conflicts = []
        is_night = self.s._is_night_shift(shift)
        is_weekend = date.fromisoformat(date_str).isoweekday() >= 6

        # 排领导：由排班模板的 leader_enabled 开关控制，leader_min 必须 > 0
        if shift.leader_enabled and shift.leader_min > 0:
            leaders, lc = self.s._assign_leaders(shift, date_str, available_ids, is_night, is_weekend)
            for lid in leaders:
                if lid not in result.leader_ids:
                    result.leader_ids.append(lid)
                result.member_ids.append(lid)
            conflicts.extend(lc)

        # 特殊人员组
        if shift.special_enabled:
            special_ids, sc = self._assign_special_group(shift, date_str, result.member_ids)
            result.member_ids.extend(special_ids)
            conflicts.extend(sc)

        # 排成员（排除已分配的人 + 整个特殊人员池）
        leader_set = set(result.leader_ids)
        already_non_leader = [
            sid for sid in result.member_ids if sid not in leader_set
        ]
        remaining_slots = max(0, shift.member_max - len(already_non_leader))
        members, mc = self._assign_members(
            shift, date_str, available_ids, result.member_ids, max_slots=remaining_slots,
        )
        result.member_ids.extend(members)
        conflicts.extend(mc)
        return conflicts

    def _assign_special_group(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        already_assigned: list[int],
    ) -> tuple[list[int], list[str]]:
        """分配特殊人员组（支持按月轮换）。

        特殊人员池是权威来源 —— 不检查 available_ids，不经过约束过滤，
        只要人员存在于组织中且未被本班次分配，则强制排入。
        """
        conflicts: list[str] = []
        special_pool = shift.special_pool or []
        count = shift.special_count

        if not special_pool:
            conflicts.append(
                f"[诊断] {shift.name}：special_pool 为空，跳过特殊人员分配"
            )
            return [], conflicts

        if not shift.special_enabled:
            conflicts.append(
                f"[诊断] {shift.name}：special_enabled=False，跳过特殊人员分配"
            )
            return [], conflicts

        freq = shift.special_rotation_frequency or 'month'
        period = self.s._get_rotation_period(date_str, freq)

        # 按月偏移选取本月特殊人员
        pool_sorted = sorted(special_pool)
        start_idx = (period * count) % len(pool_sorted)
        monthly_pool: list[int] = []
        for i in range(count):
            monthly_pool.append(pool_sorted[(start_idx + i) % len(pool_sorted)])

        # 诊断：每个模板仅输出一次
        diag_sp_key = f"_diag_special_{shift.id}"
        if not getattr(self.s, diag_sp_key, False):
            setattr(self.s, diag_sp_key, True)
            self.s._diag_msgs.append(
                f"[诊断-特殊] {shift.name}："
                f"special_freq={freq} period={period} "
                f"special_pool={special_pool} special_count={count} "
                f"本月人选={monthly_pool}"
            )

        # 特殊人员强制排入：只校验存在性（staff_map）和重复性（already_assigned）
        selected: list[int] = []
        assigned_set = set(already_assigned)
        for sid in monthly_pool:
            if sid in assigned_set:
                conflicts.append(
                    f"[诊断] {shift.name}：本月特殊人员(ID:{sid})已被分配，跳过"
                )
                continue
            if sid not in self.s.staff_map:
                conflicts.append(
                    f"{date_str} {shift.name}：特殊人员池中人员(ID:{sid})不在本组织 staff_map 中，已跳过"
                )
                continue
            selected.append(sid)
            assigned_set.add(sid)

        if len(selected) < count:
            conflicts.append(
                f"{date_str} {shift.name}：特殊人员组可用人数不足，需{count}人，仅{len(selected)}人可用"
                f" (当月候选: {monthly_pool}, staff_map_keys: {list(self.s.staff_map.keys())[:10]}...)"
            )

        return selected, conflicts

    def _assign_members(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        already_assigned: list[int],
        max_slots: int | None = None,
    ) -> tuple[list[int], list[str]]:
        conflicts: list[str] = []
        excluded = set(already_assigned)

        # 领导候选人全局排除：只能当值班领导，不参与任何班次的普通值班
        if getattr(self.s, '_all_leader_candidates', None):
            excluded |= self.s._all_leader_candidates

        # 特殊人员池的所有人都不参与普通值班（不能同时出现在同一班次）
        if shift.special_enabled and shift.special_exclude_from_member:
            excluded |= set(shift.special_pool or [])

        # 月轮班次锁定人员整月独占，日轮班次排除他们
        is_monthly = (shift.member_rotation_frequency or 'day') in ('week', 'month')
        if not is_monthly and self.s._monthly_locked:
            excluded |= self.s._monthly_locked

        candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, excluded)

        if max_slots is None:
            max_slots = shift.member_max
        target = min(max_slots, len(candidates))

        # === 诊断：每个模板前3天输出一次 ===
        freq = shift.member_rotation_frequency or 'day'
        diag_key = f"_diag_member_{shift.id}_{date_str}"
        diag_count_key = f"_diag_member_cnt_{shift.id}"
        cnt = getattr(self.s, diag_count_key, 0)
        if cnt < 3 and not getattr(self.s, diag_key, False):
            setattr(self.s, diag_key, True)
            setattr(self.s, diag_count_key, cnt + 1)
            self.s._diag_msgs.append(
                f"[诊断-成员] {shift.name} {date_str}："
                f"freq={freq} max_slots={max_slots} target={target} "
                f"candidates={len(candidates)} excluded={len(excluded)} "
                f"available={len(available_ids)}"
            )

        if len(candidates) < shift.member_min:
            conflicts.append(
                f"{date_str} {shift.name}：可用人员不足，最少需{shift.member_min}人，仅{len(candidates)}人可用"
            )

        if target <= 0 or not candidates:
            return [], conflicts

        selected = self._pair_select(candidates, date_str, target, shift)
        return selected, conflicts

    def _pair_select(
        self,
        candidates: list[int],
        date_str: str,
        target: int,
        shift: SchShiftTemplate,
    ) -> list[int]:
        """白夜交替 + 周期轮换选择。

        日轮(freq=day)：按班次次数公平排序 + 交替惩罚，逐日变化。
        周轮/月轮(freq=week/month)：稳定排序 + 周期偏移，
        同一周期内完全固定人选，不同周期不同人选。
        """
        is_night = self.s._is_night_shift(shift)
        target_type = "night" if is_night else "day"
        freq = shift.member_rotation_frequency or 'day'
        period = self.s._get_rotation_period(date_str, freq)

        if not candidates or target <= 0:
            return []
        if target >= len(candidates):
            return list(candidates)

        if freq == "day":
            # === 日轮：公平排序（本轮总次数 → 本轮同类型次数 → 日轮转偏移） ===
            # 只用本轮计数，不参杂历史数据，每人从 0 开始公平竞争
            dt = date.fromisoformat(date_str)
            day_seed = dt.day + dt.month * 31
            combined = sorted(candidates, key=lambda sid: (
                self.s._night_shifts.get(sid, 0) + self.s._day_shifts.get(sid, 0),
                self.s._night_shifts.get(sid, 0) if is_night else self.s._day_shifts.get(sid, 0),
                (sid * day_seed) % 997,
            ))
            return combined[:target]

        # === 周轮/月轮：按 ID 排序 + 周期偏移 → 纯数学轮换，不依赖历史 ===
        stable_sorted = sorted(candidates)
        n = len(stable_sorted)
        start = (period * target) % n
        selected: list[int] = []
        for i in range(target):
            selected.append(stable_sorted[(start + i) % n])

        # 诊断：每个模板仅输出一次
        diag_key = f"_diag_pair_{shift.id}_{freq}_{period}"
        if not getattr(self, diag_key, False):
            setattr(self, diag_key, True)
            selected_names = [
                self.s.staff_map.get(sid).name if self.s.staff_map.get(sid) else str(sid)
                for sid in selected
            ]
            # diagnostic stored for report (not returned as conflict, but via shifts list)
            self.s._diag_msgs.append(
                f"[诊断-月轮] {shift.name}：freq={freq} period={period} "
                f"target={target} candidates={n} start={start} "
                f"选中={selected_names}"
            )

        return selected


# ====================================================================== #
#  自动排班引擎
# ====================================================================== #

class AutoScheduler:
    """自动排班引擎

    核心职责：
    - 按天遍历、按班次遍历
    - 执行逐人轮询排班策略
    - 维护公平性打分器状态
    - 生成报告
    """

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
    ):
        self.staff_list = staff_list
        self.shift_templates: dict[int, SchShiftTemplate] = {s.id: s for s in shift_templates}
        self.constraints = sorted(
            [c for c in constraints if c.enabled], key=lambda x: x.priority or 999
        )
        self.existing_schedules = existing_schedules
        self.existing_details = existing_details
        self.staff_tag_roles_map = staff_tag_roles_map or {}
        self.org_max_ratio = org_max_ratio

        # 人员索引
        self.staff_map: dict[int, OrgStaff] = {s.id: s for s in staff_list}
        self.staff_ids: list[int] = [s.id for s in staff_list]

        # 约束参数索引
        self.constraint_params: dict[str, dict] = {
            c.rule_type: c.params or {} for c in self.constraints
        }

        # 特殊规则索引
        self.staff_special_rules: dict[int, list[SchSpecialRule]] = defaultdict(list)
        for r in special_rules:
            self.staff_special_rules[r.staff_id].append(r)

        # 公平性打分器
        self.scorer = FairnessScorer(existing_schedules, existing_details, self.shift_templates)

        # 冻结本轮开始前的排班计数快照（月轮/周轮时用于保证期内人选稳定）
        self._initial_shift_counts: dict[int, int] = {
            sid: len(self.scorer.staff_days.get(sid, set())) for sid in self.staff_ids
        }

        # 诊断消息
        self._diag_msgs: list[str] = []

        # 本轮白班/夜班计数（用于平衡同类型班次分布）
        self._night_shifts: dict[int, int] = defaultdict(int)
        self._day_shifts: dict[int, int] = defaultdict(int)

        # 月轮班次已锁定人员（整月独占，不参与白夜班）
        self._monthly_locked: set[int] = set()

        # 候选人过滤链
        self.candidate_filter = CandidateFilter(
            staff_special_rules=self.staff_special_rules,
            constraint_params=self.constraint_params,
            existing_details=existing_details,
            existing_schedules=existing_schedules,
            shift_templates=self.shift_templates,
            scorer=self.scorer,
        )

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def _is_new_employee(self, staff_id: int) -> bool:
        """通过标识体系判断是否为新员工（用于新老搭配逻辑）。"""
        if "新员工" in self.staff_tag_roles_map.get(staff_id, []):
            return True
        staff = self.staff_map.get(staff_id)
        if staff and staff.tags and "新员工" in staff.tags:
            return True
        return False

    def _get_rotation_period(self, date_str: str, freq: str) -> int:
        """获取轮换周期索引，用于周轮/月轮等。

        周轮使用相对周期（从排班起始周的周一为 0），确保同周人选一致。
        月轮使用绝对年月索引。
        """
        dt = date.fromisoformat(date_str)
        if freq == "week":
            start = getattr(self, '_rotation_start_date', None)
            if start:
                start_monday = start - timedelta(days=start.weekday())
                return max(0, (dt - start_monday).days // 7)
            return dt.isocalendar()[1]
        if freq == "month":
            return dt.year * 12 + dt.month
        return dt.timetuple().tm_yday

    def generate(
        self,
        start_date: date,
        end_date: date,
        org_id: int,
        shift_template_ids: list[int],
        staff_ids: list[int],
        leader_offsets: dict[int, int] | None = None,
    ) -> dict:
        """生成排班表。

        leader_offsets: {shift_id: iso_week_offset}，用于领导周轮跨月连续。
        首次排班 offset = start_date 所在 ISO 周号。
        """
        results: list[ScheduleResult] = []
        all_conflicts: list[str] = []

        # 轮换周期基准日期（周轮从排班起始周的周一计入周期 0）
        self._rotation_start_date = start_date
        # 领导跨月偏移量（ISO 周号基准）
        self._leader_offsets: dict[int, int] = leader_offsets or {}

        # 过滤可用人员
        available_ids = [
            s.id for s in self.staff_list
            if s.id in staff_ids and s.status == 1
        ]

        # 过滤激活的班次模板
        active_shifts = [
            self.shift_templates[sid]
            for sid in shift_template_ids
            if sid in self.shift_templates and self.shift_templates[sid].status == 1
        ]

        # 强制纳入所有模板的 special_pool 人员（即使未在 staff_ids 中选择）
        for shift in active_shifts:
            if shift.special_enabled:
                for sid in (shift.special_pool or []):
                    if sid in self.staff_map and sid not in available_ids:
                        available_ids.append(sid)

        # 收集全局领导候选人 + 强制纳入 available_ids（即使未在 staff_ids 中选择）
        self._all_leader_candidates: set[int] = set()
        for shift in active_shifts:
            if not shift.leader_enabled:
                continue
            if shift.leader_pool:
                for sid in shift.leader_pool:
                    if sid not in self.staff_map:
                        continue
                    self._all_leader_candidates.add(sid)
                    if sid not in available_ids:
                        available_ids.append(sid)
            elif shift.leader_use_tag:
                # 无候选池 → 用排班模板指定的标签名筛选标识人员
                tag_name = getattr(shift, 'leader_tag_name', None) or '领导'
                tagged_count = 0
                for s in self.staff_list:
                    sid = s.id
                    old_has = bool(s.tags and tag_name in (s.tags or []))
                    new_has = tag_name in self.staff_tag_roles_map.get(sid, [])
                    if (old_has or new_has) and s.status == 1:
                        self._all_leader_candidates.add(sid)
                        if sid not in available_ids:
                            available_ids.append(sid)
                        tagged_count += 1
                self._diag_msgs.append(
                    f"[诊断-领导池] leader_pool=None, tag_name={tag_name}, "
                    f"tagged_found={tagged_count} staff_list={len(self.staff_list)}"
                )

        # === 诊断：检查特殊人员组和成员组的频次是否匹配 ===
        for shift in active_shifts:
            if shift.special_enabled:
                member_freq = shift.member_rotation_frequency or 'day'
                special_freq = shift.special_rotation_frequency or 'month'
                self._diag_msgs.append(
                    f"[诊断-频次] {shift.name}："
                    f"member_freq={member_freq} special_freq={special_freq} "
                    f"member_max={shift.member_max} special_count={shift.special_count} "
                    f"special_pool={shift.special_pool}"
                )

        # 排序：月轮/周轮模板排在前，日轮模板排在后
        # 确保行政班等固定人选的班次先占人，白夜班再竞争剩余人员
        active_shifts.sort(key=lambda s: (
            0 if (s.member_rotation_frequency or 'day') in ('week', 'month') else 1
        ))

        # 预构建模板级约束索引
        all_constraint_map = {c.id: c for c in self.constraints}

        # 预算每日可排人数上限
        total_staff = len(available_ids)
        daily_max_count = None
        if self.org_max_ratio and total_staff > 0:
            daily_max_count = max(1, int(total_staff * self.org_max_ratio))

        # 策略实例（始终使用逐人轮询）
        strategy = IndividualStrategy(self)

        # 标记本轮开始日期，MAX_CONTINUOUS_DAYS 不跨月串联
        self.candidate_filter._run_start_str = str(start_date)

        # 跨月均衡：把上月末最后 3 天的排班继承到本轮初始计数
        tail_start = start_date - timedelta(days=3)
        tail_start_str = str(tail_start)
        start_date_str = str(start_date)
        sched_idx = {s.id: s for s in self.existing_schedules}
        for d in self.existing_details:
            s = sched_idx.get(d.schedule_id)
            if s:
                d_str = str(getattr(s, "date", ""))
                if tail_start_str <= d_str < start_date_str:
                    shift_t = self.shift_templates.get(getattr(s, "shift_id", None))
                    if shift_t and self._is_night_shift(shift_t):
                        self._night_shifts[d.staff_id] = self._night_shifts.get(d.staff_id, 0) + 1
                    elif shift_t:
                        self._day_shifts[d.staff_id] = self._day_shifts.get(d.staff_id, 0) + 1

        current = start_date
        while current <= end_date:
            date_str = str(current)
            weekday = current.isoweekday()

            for shift in active_shifts:
                if weekday not in (shift.apply_days or [1, 2, 3, 4, 5, 6, 7]):
                    continue

                # 按模板 constraint_ids 过滤约束规则
                template_constraint_ids = shift.constraint_ids
                if template_constraint_ids:
                    template_constraints = [
                        all_constraint_map[cid]
                        for cid in template_constraint_ids
                        if cid in all_constraint_map
                    ]
                else:
                    template_constraints = self.constraints
                # 临时替换 candidate_filter 的约束参数
                orig_constraint_params = self.candidate_filter._constraint_params
                self.candidate_filter._constraint_params = {
                    c.rule_type: c.params or {} for c in template_constraints
                }

                result = ScheduleResult(date_str, shift.id, org_id)
                conflicts = strategy.assign(
                    shift, date_str, available_ids, result,
                )
                result.conflicts.extend(conflicts)
                all_conflicts.extend(conflicts)

                # 恢复全局约束参数
                self.candidate_filter._constraint_params = orig_constraint_params

                # 去重
                result.member_ids = list(dict.fromkeys(result.member_ids))

                # 检查组织每日排班人数上限
                if daily_max_count:
                    already_today = len([
                        sid for sid in available_ids
                        if date_str in self.scorer.staff_days.get(sid, set())
                    ])
                    remaining_quota = daily_max_count - already_today
                    if remaining_quota <= 0:
                        result.member_ids = []
                        result.conflicts.append(
                            f"{date_str} {shift.name}：组织每日排班人数已达上限({daily_max_count}人)，已跳过"
                        )
                    elif len(result.member_ids) > remaining_quota:
                        result.member_ids = result.member_ids[:remaining_quota]

                # 记录到打分器
                for sid in result.member_ids:
                    self.scorer.record_assignment(sid, date_str, shift.id)

                # 记录白班/夜班计数（用于同类型班次平衡）
                if self._is_night_shift(shift):
                    for sid in result.member_ids:
                        self._night_shifts[sid] = self._night_shifts.get(sid, 0) + 1
                else:
                    for sid in result.member_ids:
                        self._day_shifts[sid] = self._day_shifts.get(sid, 0) + 1

                # 兜底截断
                result.member_ids = self._truncate_members(result, shift)

                # 月轮班次：首次分配后锁定其普通成员，整月排除
                is_monthly = (shift.member_rotation_frequency or 'day') in ('week', 'month')
                if is_monthly and not self._monthly_locked and result.member_ids:
                    special_ids = set(shift.special_pool or []) if shift.special_enabled else set()
                    leader_set = set(result.leader_ids)
                    locked = [
                        sid for sid in result.member_ids
                        if sid not in leader_set and sid not in special_ids
                    ]
                    if locked:
                        self._monthly_locked.update(locked)
                        self._diag_msgs.append(
                            f"[诊断-锁定] {shift.name}：锁定普通成员={locked}"
                        )

                results.append(result)

            current += timedelta(days=1)

        report = self._build_report(results)
        return {
            "schedules": results,
            "report": report,
            "conflicts": all_conflicts,
            "diagnostics": self._diag_msgs,
        }

    # ------------------------------------------------------------------ #
    #  领导分配
    # ------------------------------------------------------------------ #

    def _assign_leaders(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        is_night: bool,
        is_weekend: bool,
    ) -> tuple[list[int], list[str]]:
        conflicts: list[str] = []

        # 确定候选池：leader_pool → 身份标识"领导" → 空（不安排）
        if shift.leader_pool:
            candidates = [sid for sid in shift.leader_pool if sid in available_ids]
        else:
            tagged = []
            tag_name = getattr(shift, 'leader_tag_name', None) or '领导'
            for s in self.staff_list:
                if s.id not in available_ids:
                    continue
                old_has = bool(s.tags and tag_name in (s.tags or []))
                new_has = tag_name in self.staff_tag_roles_map.get(s.id, [])
                if old_has or new_has:
                    tagged.append(s.id)
            candidates = tagged

        # 保存完整候选池（过滤前），用于周轮/月轮索引计算
        full_pool = list(candidates)

        # 领导候选人仅过特殊规则 + MAX_SHIFTS_PER_DAY，不过 MAX_CONTINUOUS_DAYS
        # （同一周每天同一领导不应因连续天数被排除）
        candidates = self.candidate_filter._filter_by_special_rules(
            list(candidates), date_str, shift.id
        )
        # 仅检查当天是否已排班（避免同一人同天被排两次）
        max_per_day = self.candidate_filter._constraint_params.get(
            "MAX_SHIFTS_PER_DAY", {}
        ).get("count", 1)
        candidates = [
            sid for sid in candidates
            if self.candidate_filter._count_today(sid, date_str) < max_per_day
        ]

        if not candidates:
            if shift.leader_min > 0:
                conflicts.append(
                    f"{date_str} {shift.name}：领导候选不足，最少需{shift.leader_min}人，但无可用候选人"
                )
            return [], conflicts

        leader_freq = shift.leader_rotation_frequency or 'week'
        leader_count = shift.leader_count

        # 按周期轮换选取（周轮/月轮），同一周期内固定人选
        if leader_freq in ("week", "month"):
            if leader_freq == "week":
                # 领导周轮：使用绝对 ISO 周号 - 偏移量，确保跨月连续
                iso_week = date.fromisoformat(date_str).isocalendar()[1]
                leader_offset = self._leader_offsets.get(shift.id, iso_week)
                period = iso_week - leader_offset
            else:
                period = self._get_rotation_period(date_str, leader_freq)
            # 基于完整候选池大小计算轮换索引，确保同周每天人选一致
            full_sorted = sorted(full_pool)
            full_count = max(1, len(full_sorted))
            start_idx = (period * leader_count) % full_count
            # 从过滤后的候选中按索引顺序选取，被过滤的跳过，环形向后找
            filtered_set = set(candidates)
            selected = []
            for i in range(full_count):
                idx = (start_idx + i) % full_count
                sid = full_sorted[idx]
                if sid in filtered_set and sid not in selected:
                    selected.append(sid)
                if len(selected) >= leader_count:
                    break
            # 诊断：每个周期只输出一次领导选择日志
            diag_leader_key = f"_diag_leader_{shift.id}_{period}"
            if not getattr(self, diag_leader_key, False):
                setattr(self, diag_leader_key, True)
                self._diag_msgs.append(
                    f"[诊断-领导] {shift.name} period={period}（{leader_freq}） "
                    f"full_pool={full_sorted} filtered={sorted(candidates)} "
                    f"start_idx={start_idx} selected={selected}"
                )
        else:
            # 日轮：打分排序选取
            scored = [
                (sid, self.scorer.score(sid, date_str, shift.id, is_night, is_weekend))
                for sid in candidates
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            selected = [sid for sid, _ in scored[:leader_count]]

        available_count = len(selected)
        target = min(leader_count, available_count)

        if available_count < shift.leader_min:
            conflicts.append(
                f"{date_str} {shift.name}：领导候选不足，最少需{shift.leader_min}人，仅{available_count}人可用"
            )

        return selected[:target], conflicts

    # ------------------------------------------------------------------ #
    #  公共选取逻辑（分层轮转）
    # ------------------------------------------------------------------ #

    def _tier_rotate_select(
        self, candidates: list[int], date_str: str, target: int,
    ) -> list[int]:
        """按排班次数分层，次数少的优先；同层内按日期偏移轮转。"""
        count_map = {sid: len(self.scorer.staff_days.get(sid, set())) for sid in candidates}
        candidates_sorted = sorted(candidates, key=lambda sid: (count_map[sid], sid))

        if target >= len(candidates_sorted):
            return candidates_sorted

        min_count = count_map[candidates_sorted[0]]
        min_tier = [sid for sid in candidates_sorted if count_map[sid] == min_count]
        rest_tier = [sid for sid in candidates_sorted if count_map[sid] > min_count]

        dt_obj = date.fromisoformat(date_str)
        offset = (dt_obj.timetuple().tm_yday * target) % len(min_tier) if min_tier else 0
        rotated = min_tier[offset:] + min_tier[:offset]
        selected = rotated[:target]

        remaining = target - len(selected)
        if remaining > 0 and rest_tier:
            rest_sorted = sorted(rest_tier, key=lambda sid: (count_map[sid], sid))
            rest_start = (dt_obj.timetuple().tm_yday * remaining) % len(rest_sorted)
            rest_rotated = rest_sorted[rest_start:] + rest_sorted[:rest_start]
            selected.extend(rest_rotated[:remaining])

        return selected

    # ------------------------------------------------------------------ #
    #  工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _truncate_members(result: ScheduleResult, shift: SchShiftTemplate) -> list[int]:
        """截断超出上限的成员，但特殊人员不会被截断。"""
        members = result.member_ids
        leader_set = set(result.leader_ids)
        leader_part = [lid for lid in members if lid in leader_set]
        non_leader = [mid for mid in members if mid not in leader_set]

        special_ids: set[int] = set()
        if shift.special_enabled:
            special_ids = set(shift.special_pool or [])

        special_in = [mid for mid in non_leader if mid in special_ids]
        regular_in = [mid for mid in non_leader if mid not in special_ids]

        # 领导上限取 leader_max 和 leader_count 中较大者，确保 selected 不会被截掉
        leader_cap = max(shift.leader_max, shift.leader_count, len(leader_part))
        effective_max = leader_cap + shift.member_max + len(special_in)

        if len(members) > effective_max:
            regular_in = regular_in[:shift.member_max]
            return leader_part[:leader_cap] + special_in + regular_in

        if len(regular_in) > shift.member_max:
            regular_in = regular_in[:shift.member_max]
            return leader_part + special_in + regular_in

        return members

    @staticmethod
    def _is_night_shift(shift: SchShiftTemplate) -> bool:
        try:
            sh, _ = map(int, shift.start_time.split(":"))
            eh, _ = map(int, shift.end_time.split(":"))
            return sh >= 20 or eh <= 8
        except (ValueError, AttributeError):
            return False

    # ------------------------------------------------------------------ #
    #  报告生成
    # ------------------------------------------------------------------ #

    def _build_report(self, results: list[ScheduleResult]) -> dict:
        total_shifts = len(results)
        total_staff = len(self.staff_list)

        staff_hours: dict[int, float] = defaultdict(float)
        night_dist: dict[int, int] = defaultdict(int)

        for r in results:
            shift = self.shift_templates.get(r.shift_id)
            if not shift:
                continue
            dur = FairnessScorer._calc_duration(shift.start_time, shift.end_time)
            is_night = self._is_night_shift(shift)
            for sid in r.member_ids:
                staff_hours[sid] += dur
                if is_night:
                    night_dist[sid] += 1

        avg_hours = sum(staff_hours.values()) / max(total_staff, 1)

        return {
            "total_shifts": total_shifts,
            "total_staff": total_staff,
            "avg_hours_per_person": round(avg_hours, 1),
            "staff_hours": {sid: round(h, 1) for sid, h in staff_hours.items()},
            "night_distribution": {sid: cnt for sid, cnt in night_dist.items()},
        }
