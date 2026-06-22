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
        pre_history: dict[int, list[str]] | None = None,
    ):
        self._staff_special_rules = staff_special_rules
        self._constraint_params = constraint_params
        self._existing_details = existing_details
        self._schedule_index: dict[int, object] = {s.id: s for s in existing_schedules}
        self._shift_templates = shift_templates
        self._scorer = scorer
        self._pre_history = pre_history or {}

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
        # 合并 pre_history（上月末尾排班数据）
        pre = self._pre_history.get(staff_id, [])
        if pre:
            all_dates_raw = sorted(set(all_dates_raw) | set(pre))
        # 只统计本轮排班开始后的日期，避免跨月历史数据串联
        run_start = getattr(self, '_run_start_str', '0000-01-01')
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
#  槽位分组器（核心规则）
# ====================================================================== #

class SlotGrouper:
    """跨月槽位分组器

    规则：
    - 按 ID 排序人员，分3槽，每槽4人
    - 每槽前2人为一组（白班组/夜班组），后2人为一组
    - 新老搭配：每2人组中1新+1老
    - 跨月1对1替换
    """

    def __init__(self, staff_map: dict[int, OrgStaff], is_new_employee_fn):
        self._staff_map = staff_map
        self._is_new = is_new_employee_fn
        self._month_groups: dict[int, tuple[list[int], list[int]]] = {}
        self._current_month: int = 0
        self._prev_month_groups: dict[int, tuple[list[int], list[int]]] = {}

    def get_month_groups(
        self,
        sorted_ids: list[int],
        year: int,
        month: int,
    ) -> dict[int, tuple[list[int], list[int]]]:
        """获取或构建指定月份的槽位绑定。"""
        month_key = year * 12 + month

        # 月份切换：保存上月绑定
        if self._current_month and self._current_month != month_key:
            self._prev_month_groups = dict(self._month_groups)
            self._month_groups = {}
            self._current_month = month_key

        if self._month_groups:
            return self._month_groups

        # 尝试跨月替换
        if self._prev_month_groups and self._can_reuse_prev(sorted_ids):
            self._month_groups = self._apply_cross_month_replacement(sorted_ids)
            return self._month_groups

        # 新建绑定
        self._month_groups = self._build_groups(sorted_ids)
        self._current_month = month_key
        return self._month_groups

    def _can_reuse_prev(self, sorted_ids: list[int]) -> bool:
        """检查上月绑定是否可以复用。"""
        prev_all = set()
        for dg, ng in self._prev_month_groups.values():
            prev_all.update(dg)
            prev_all.update(ng)
        curr_all = set(sorted_ids)
        departed = prev_all - curr_all
        joined = curr_all - prev_all
        # 有变更也可复用（由替换逻辑处理）
        return True

    def _apply_cross_month_replacement(
        self, sorted_ids: list[int],
    ) -> dict[int, tuple[list[int], list[int]]]:
        """跨月1对1替换：上月有人离开，新人替入同槽位。"""
        prev_all = set()
        for dg, ng in self._prev_month_groups.values():
            prev_all.update(dg)
            prev_all.update(ng)
        curr_all = set(sorted_ids)

        departed = sorted(prev_all - curr_all)
        joined = sorted(curr_all - prev_all)

        if not departed and not joined:
            return dict(self._prev_month_groups)

        # 1对1替换
        replacements = dict(zip(departed, joined))
        new_groups = {}
        for slot_idx, (dg, ng) in self._prev_month_groups.items():
            new_dg = [replacements.get(sid, sid) for sid in dg if sid in curr_all or sid in replacements]
            new_ng = [replacements.get(sid, sid) for sid in ng if sid in curr_all or sid in replacements]
            new_groups[slot_idx] = (new_dg, new_ng)

        # 如果有新加入但未被分配的人，添加到人数最少的槽位
        assigned = set()
        for dg, ng in new_groups.values():
            assigned.update(dg)
            assigned.update(ng)
        unassigned = [sid for sid in joined if sid not in assigned]
        if unassigned:
            min_slot = min(new_groups.keys(), key=lambda k: len(new_groups[k][0]) + len(new_groups[k][1]))
            dg, ng = new_groups[min_slot]
            for sid in unassigned:
                if len(dg) <= len(ng):
                    dg.append(sid)
                else:
                    ng.append(sid)
            new_groups[min_slot] = (dg, ng)

        return new_groups

    def _build_groups(
        self, sorted_ids: list[int],
    ) -> dict[int, tuple[list[int], list[int]]]:
        """构建新绑定：新老搭配 + 均匀分配到3槽。"""
        n = len(sorted_ids)
        if n == 0:
            return {}

        # 按新老分组
        new_ids = [sid for sid in sorted_ids if self._is_new(sid)]
        old_ids = [sid for sid in sorted_ids if not self._is_new(sid)]

        # 交叉配对：优先1新+1老
        pairs: list[list[int]] = []
        while new_ids and old_ids:
            pairs.append([new_ids.pop(0), old_ids.pop(0)])
        while len(new_ids) >= 2:
            pairs.append([new_ids.pop(0), new_ids.pop(0)])
        while len(old_ids) >= 2:
            pairs.append([old_ids.pop(0), old_ids.pop(0)])
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

        # 确定槽位数
        n_slots = 3 if n >= 9 else (2 if n >= 5 else 1)

        # 均匀分配配对到槽位
        slot_members: dict[int, list[int]] = {i: [] for i in range(n_slots)}
        for i, pair in enumerate(pairs):
            slot_idx = i % n_slots
            slot_members[slot_idx].extend(pair)

        # 每槽分为 day_group(前2) 和 night_group(后2)
        groups: dict[int, tuple[list[int], list[int]]] = {}
        for slot_idx in range(n_slots):
            members = slot_members[slot_idx]
            mid = len(members) // 2
            groups[slot_idx] = (members[:mid], members[mid:])

        return groups


# ====================================================================== #
#  排班策略
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
        if shift.special_enabled:
            self.s._current_admin_members[shift.id] = list(dict.fromkeys(result.member_ids))
        conflicts.extend(mc)
        return conflicts

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
        3. 如果没有其他班次数据，按 ID 顺序选择
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
        else:
            new_members = list(dict.fromkeys(new_members))[:count]

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
            if sid not in self.s.staff_map:
                conflicts.append(f"{date_str} {shift.name}：特殊人员池中人员(ID:{sid})不在本组织中，已跳过")
                continue
            selected.append(sid)
            assigned_set.add(sid)

        if len(selected) < count:
            source_by_member = self.s._special_source_shift_by_member
            selected_sources = {
                source_by_member[sid]
                for sid in selected
                if sid in source_by_member
            }
            def add_from_pool(strict_source: bool) -> None:
                for sid in special_pool:
                    if len(selected) >= count:
                        break
                    if sid in selected or sid in assigned_set or sid in daily:
                        continue
                    if sid not in self.s.staff_map:
                        continue
                    source_shift_id = source_by_member.get(sid)
                    if strict_source and source_shift_id in selected_sources:
                        continue
                    selected.append(sid)
                    if source_shift_id is not None:
                        selected_sources.add(source_shift_id)
                    assigned_set.add(sid)

            add_from_pool(strict_source=True)
            if len(selected) < count:
                add_from_pool(strict_source=False)

        if len(selected) < count:
            conflicts.append(f"{date_str} {shift.name}：特殊人员组可用人数不足，需{count}人，仅{len(selected)}人可用")

        # 保存当月特殊人员状态供后续推导使用
        self.s._prev_special_members[shift.id] = selected
        self.s._current_special_locked.update(selected)

        return selected, conflicts

    def _derive_prev_special_from_db(self, shift: SchShiftTemplate) -> list[int] | None:
        """从内存缓存读取上月特殊人员（由 _assign_special_group 保存）"""
        return self.s._prev_special_members.get(shift.id, None) or None

    def _derive_special_from_other_shifts(
        self, current_shift: SchShiftTemplate, pool: list[int]
    ) -> list[int] | None:
        """从上月其他班次推导本月特殊人员

        规则：特殊人员在不同班次间交替轮换。
        上月在白班/夜班的特殊人员，本月应在行政班；
        上月在行政班的特殊人员，本月应在白班/夜班。

        统计上月所有天中 pool 人员出现频率，选出现最多的 count 人。
        这样能正确继承手动调整的结果。
        """
        if not self.s.prev_month_schedules:
            return None

        pool_set = set(pool)
        count = current_shift.special_count

        source_by_member: dict[int, tuple[int, int, str]] = {}
        for shift_id, pairings in self.s._loaded_pairings.items():
            if shift_id == current_shift.id:
                continue
            for (slot_idx, group_type), (staff_ids, _) in pairings.items():
                for sid in staff_ids:
                    source_by_member[sid] = (shift_id, slot_idx, group_type)
                    self.s._special_source_shift_by_member.setdefault(
                        sid, source_by_member[sid]
                    )

        # 按 shift_id 分组上月排班
        by_shift: dict[int, list] = defaultdict(list)
        for sched in self.s.prev_month_schedules:
            if sched.shift_id == current_shift.id:
                continue
            by_shift[sched.shift_id].append(sched)

        # 遍历所有其他班次，找到有 pool 人员的班次
        source_candidates: dict[tuple[int, int, str], list[int]] = {}
        for other_shift_id in sorted(by_shift.keys()):
            schedules = by_shift[other_shift_id]
            # 收集该班次所有天的 pool 人员出现次数
            freq: dict[int, int] = defaultdict(int)
            for sched in schedules:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id and d.staff_id in pool_set:
                        freq[d.staff_id] += 1

            if not freq:
                continue

            # 按频率降序，频率相同按 ID 升序
            sorted_by_freq = sorted(freq.keys(), key=lambda sid: (-freq[sid], sid))
            for sid in sorted_by_freq:
                source_key = source_by_member.get(sid, (other_shift_id, -1, "unknown"))
                source_candidates.setdefault(source_key, []).append(sid)
                self.s._special_source_shift_by_member.setdefault(sid, source_key)

        if not source_candidates:
            return None

        # Do not drain multiple people from the same regular shift first.
        # Return at most one person per source shift; _assign_special_group can
        # fill any remaining quota later while still preferring unused sources.
        selected: list[int] = []
        used_members: set[int] = set()
        for source_key in sorted(source_candidates):
            for sid in source_candidates[source_key]:
                if sid in used_members:
                    continue
                selected.append(sid)
                used_members.add(sid)
                break
            if len(selected) >= count:
                break

        return selected or None

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
        previous_admin_members: set[int] = set()
        if shift.special_enabled and shift.special_exclude_from_member:
            excluded |= set(shift.special_pool or [])
            for sched in self.s.prev_month_schedules:
                if sched.shift_id != shift.id:
                    continue
                for detail in self.s.existing_details:
                    if detail.schedule_id == sched.id:
                        previous_admin_members.add(detail.staff_id)
            if self.s._special_source_shift_by_member:
                excluded |= {
                    sid for sid in previous_admin_members
                    if sid in self.s._special_source_shift_by_member
                }
            else:
                excluded |= previous_admin_members

        # 月轮班次锁定人员整月独占，日轮班次排除他们
        is_monthly = (shift.member_rotation_frequency or 'day') in ('week', 'month')
        if not is_monthly and self.s._monthly_locked:
            excluded |= self.s._monthly_locked
        if not shift.special_enabled and self.s._current_special_locked:
            excluded |= self.s._current_special_locked

        candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, excluded)

        if max_slots is None:
            max_slots = shift.member_max
        target = min(max_slots, len(candidates))
        dt = date.fromisoformat(date_str)
        month_key = dt.year * 12 + dt.month
        monthly_cache_key = (shift.id, max_slots, month_key)
        if is_monthly and monthly_cache_key in self.s._monthly_member_cache:
            cached = [
                sid for sid in self.s._monthly_member_cache[monthly_cache_key]
                if sid not in excluded
            ]
            return cached[:max_slots], conflicts

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

        selected = self._slot_rotate_select(candidates, date_str, target, shift)
        if is_monthly:
            self.s._monthly_member_cache[monthly_cache_key] = list(selected)
        return selected, conflicts

    def _slot_rotate_select(
        self,
        candidates: list[int],
        date_str: str,
        target: int,
        shift: SchShiftTemplate,
    ) -> list[int]:
        """标准槽位轮转选择。

        核心规则：
        - 按ID排序，(day-1)%3分3槽
        - rotation偶数：前半白后半夜；奇数：前半夜后半白
        - 新老搭配：每2人组中1新+1老
        - 整月绑定：同槽人员整月不变
        - 跨月轮换：上月行政班的普通人员 → 本月白班/夜班，反之亦然

        重要：优先使用数据库中的配对关系，没有则用 SlotGrouper 生成。
        """
        is_night = self.s._is_night_shift(shift)
        target_type = "night" if is_night else "day"
        freq = shift.member_rotation_frequency or 'day'

        if not candidates or target <= 0:
            return []
        if freq == "day":
            dt = date.fromisoformat(date_str)
            year, month = dt.year, dt.month

            # Month lifecycle is owned by AutoScheduler.generate(). Do not clear
            # monthly locks here, otherwise day/night shifts can forget that the
            # current month's admin staff are already occupied.
            if self.s._slot_grouper._current_month != year * 12 + month:
                self.s._slot_grouper._current_month = year * 12 + month
                self.s._day_candidates_cache.clear()

            # 跨月原位替换: 有上月数据时，在上月分组中执行替换
            if self.s.prev_month_schedules and self.s._loaded_pairings.get(shift.id):
                cache_key = f"{date_str}:{target_type}"
                if cache_key not in self.s._day_candidates_cache:
                    self.s._day_candidates_cache[cache_key] = sorted(candidates)
                sorted_ids = self.s._day_candidates_cache[cache_key]
                groups = self.s._replacement_groups_cache.get(shift.id)
                if groups is None:
                    groups = self._pairings_to_groups(self.s._loaded_pairings[shift.id])

                active_group_key = None
                if groups:
                    n_slots_for_key = len(groups)
                    rotation_day_for_key = self.s._slot_rotation_day_index(dt)
                    slot_idx_for_key = rotation_day_for_key % n_slots_for_key
                    rotation_number_for_key = rotation_day_for_key // n_slots_for_key
                    if rotation_number_for_key % 2 == 0:
                        group_type_for_key = target_type
                    else:
                        group_type_for_key = "night" if target_type == "day" else "day"
                    active_group_key = (shift.id, slot_idx_for_key, group_type_for_key)

                if active_group_key not in self.s._replacement_processed_groups:
                    groups = self._apply_in_place_replacement(
                        groups, shift, sorted_ids, dt, target_type
                    )
                    if active_group_key is not None:
                        self.s._replacement_processed_groups.add(active_group_key)
                self.s._replacement_groups_cache[shift.id] = groups
                if groups:
                    self.s._new_pairings[shift.id] = self._groups_to_pairings(groups)
            else:
                cache_key = f"{date_str}:{target_type}"
                if cache_key not in self.s._day_candidates_cache:
                    self.s._day_candidates_cache[cache_key] = sorted(candidates)
                sorted_ids = self.s._day_candidates_cache[cache_key]
                groups = self.s._slot_grouper.get_month_groups(sorted_ids, year, month)

                # 首次生成时，保存配对关系供后续使用
                if groups and shift.id not in self.s._new_pairings:
                    self.s._new_pairings[shift.id] = self._groups_to_pairings(groups)

            if not groups:
                return self._fallback_select(candidates, date_str, target, is_night)

            # 标准12人场景：3槽位
            n_slots = len(groups)
            if n_slots == 0:
                return self._fallback_select(candidates, date_str, target, is_night)

            rotation_day = self.s._slot_rotation_day_index(dt)
            rotation_slot = rotation_day % n_slots
            rotation_number = rotation_day // n_slots

            dg, ng = groups[rotation_slot]

            if rotation_number % 2 == 0:
                # 偶数轮：前半白，后半夜
                selected = (dg if target_type == "day" else ng)
            else:
                # 奇数轮：前半夜，后半白
                selected = (ng if target_type == "day" else dg)

            # 过滤掉不在当前候选集中的人
            candidate_set = set(candidates) | self.s._replacement_allowed_members.get(shift.id, set())
            selected = [sid for sid in selected if sid in candidate_set]

            # 如果选出的组不足 target 人，返回整个组（不展开）
            # 槽位绑定的核心规则：同组人员整月绑定，不跨组混合
            return selected

        # === 周轮/月轮：按 ID 排序 + 周期偏移 → 纯数学轮换 ===
        if target >= len(candidates) and not shift.special_enabled:
            return list(candidates)
        period = self.s._get_rotation_period(date_str, freq)
        stable_sorted = sorted(candidates)
        n = len(stable_sorted)
        start = (period * target) % n
        rotated = [stable_sorted[(start + i) % n] for i in range(n)]
        if shift.special_enabled:
            self._ensure_source_group_map(shift)
        if shift.special_enabled and self.s._special_source_shift_by_member:
            selected_sources = {
                self.s._special_source_shift_by_member[sid]
                for sid in self.s._prev_special_members.get(shift.id, [])
                if sid in self.s._special_source_shift_by_member
            }
            selected: list[int] = []
            for sid in rotated:
                source_key = self.s._special_source_shift_by_member.get(sid)
                if source_key is None:
                    continue
                if source_key in selected_sources:
                    continue
                selected.append(sid)
                selected_sources.add(source_key)
                if len(selected) >= target:
                    return selected
            for sid in rotated:
                source_key = self.s._special_source_shift_by_member.get(sid)
                if source_key is None:
                    if sid not in selected:
                        selected.append(sid)
                    if len(selected) >= target:
                        return selected
                    continue
                if source_key in selected_sources:
                    continue
                if sid not in selected:
                    selected.append(sid)
                    selected_sources.add(source_key)
                if len(selected) >= target:
                    return selected
            return selected
        return rotated[:target]

    def _ensure_source_group_map(self, current_shift: SchShiftTemplate) -> None:
        for shift_id, pairings in self.s._loaded_pairings.items():
            if shift_id == current_shift.id:
                continue
            for (slot_idx, group_type), (staff_ids, _) in pairings.items():
                for sid in staff_ids:
                    self.s._special_source_shift_by_member.setdefault(
                        sid, (shift_id, slot_idx, group_type)
                    )

    def _apply_in_place_replacement(
        self,
        groups: dict[int, tuple[list[int], list[int]]],
        shift: SchShiftTemplate,
        sorted_ids: list[int],
        schedule_date: date | None = None,
        target_type: str = "day",
    ) -> dict[int, tuple[list[int], list[int]]]:
        """跨月原位替换：在上月分组中直接替换人员。

        规则：
        1. 特殊人员：上月行政班的特殊人员 -> 本月替换上月白班/夜班的特殊人员
        2. 普通人员：上月行政班的普通人员 -> 本月替换上月白班/夜班的普通人员
        3. 按 ID 排序后一一对应替换
        """
        if not groups or not self.s.prev_month_schedules:
            return groups


        # 找到行政班
        admin_shift = None
        for sid, s in self.s.shift_templates.items():
            if s.id != shift.id and s.special_enabled:
                admin_shift = s
                break
        if not admin_shift or admin_shift.id == shift.id:
            return groups

        # 上月行政班的所有人员（取第一天）
        people_from_admin = []
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == admin_shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id:
                        if d.staff_id not in people_from_admin:
                            people_from_admin.append(d.staff_id)

        # 上月本班次（白班/夜班）人员（取第一天）
        people_from_slot = []
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id:
                        if d.staff_id not in people_from_slot:
                            people_from_slot.append(d.staff_id)
                break

        if not people_from_admin or not people_from_slot:
            return groups

        current_admin_order = list(
            self.s._current_admin_members.get(admin_shift.id)
            or self.s._prev_special_members.get(admin_shift.id, [])
        )
        prev_group_people = [
            sid
            for slot_idx in sorted(groups)
            for group in groups[slot_idx]
            for sid in group
        ]
        prev_group_set = set(prev_group_people)
        candidate_set = set(sorted_ids)
        departed_set = (
            set(current_admin_order)
            | set(self.s._monthly_locked)
            | set(self.s._current_special_locked)
        )
        scoped_group_people = prev_group_people
        if schedule_date is not None and groups:
            n_slots = len(groups)
            rotation_day = self.s._slot_rotation_day_index(schedule_date)
            rotation_slot = rotation_day % n_slots
            rotation_number = rotation_day // n_slots
            day_group, night_group = groups[rotation_slot]
            if rotation_number % 2 == 0:
                scoped_group_people = day_group if target_type == "day" else night_group
            else:
                scoped_group_people = night_group if target_type == "day" else day_group

        departed = [sid for sid in scoped_group_people if sid in departed_set]
        if departed:
            departed_set_for_group = set(departed)
            departed.extend(
                sid for sid in scoped_group_people
                if sid not in candidate_set and sid not in departed_set_for_group
            )
        elif not departed_set:
            # Unit-level callers may invoke replacement without preparing the
            # monthly special lock. Keep the legacy fallback for that narrow
            # case, but never let daily candidate filtering mutate live pairings
            # once the month's admin/special roster is known.
            departed = [sid for sid in scoped_group_people if sid not in candidate_set]

        replacements: dict[int, int] = {}
        used_replacements = set(self.s._replacement_used_members)
        current_replacements: set[int] = set()
        fallback_admin = [
            sid for sid in people_from_admin
            if sid not in used_replacements
        ]
        ordered_departed = sorted(
            departed,
            key=lambda sid: (
                sid not in self.s._admin_replacement_map
                and sid not in current_admin_order,
                current_admin_order.index(sid) if sid in current_admin_order else len(current_admin_order),
                sid,
            ),
        )
        for old_sid in ordered_departed:
            new_sid = None
            if old_sid in self.s._admin_replacement_map:
                candidate = self.s._admin_replacement_map[old_sid]
                if candidate not in current_replacements:
                    new_sid = candidate
            elif old_sid in current_admin_order:
                idx = current_admin_order.index(old_sid)
                if idx < len(people_from_admin):
                    candidate = people_from_admin[idx]
                    if candidate not in current_replacements:
                        new_sid = candidate
                        self.s._admin_replacement_map[old_sid] = new_sid
            while new_sid is None and fallback_admin:
                candidate = fallback_admin.pop(0)
                if candidate in used_replacements or candidate in current_replacements:
                    continue
                new_sid = candidate
                self.s._admin_replacement_map[old_sid] = new_sid
            if new_sid is None:
                continue
            replacements[old_sid] = new_sid
            current_replacements.add(new_sid)
            used_replacements.add(new_sid)

        if not replacements:
            return groups

        self.s._replacement_allowed_members.setdefault(shift.id, set()).update(
            replacements.values()
        )
        self.s._replacement_used_members.update(replacements.values())

        new_groups: dict[int, tuple[list[int], list[int]]] = {}
        def replacement_priority(old_sid: int) -> tuple[int, int]:
            if old_sid in current_admin_order:
                return (0, current_admin_order.index(old_sid))
            return (1, old_sid)

        def apply_replacements(group: list[int]) -> list[int]:
            if group and all(sid in replacements for sid in group):
                ordered = sorted(group, key=replacement_priority)
                return [replacements[sid] for sid in ordered]
            return [replacements.get(sid, sid) for sid in group]

        for slot_idx in sorted(groups):
            dg, ng = groups[slot_idx]
            new_groups[slot_idx] = (
                apply_replacements(dg),
                apply_replacements(ng),
            )

        if schedule_date is not None:
            protected_candidates = list(dict.fromkeys(list(replacements.values()) + sorted_ids))
            return self._normalize_current_replaced_group(
                new_groups, groups, protected_candidates, schedule_date, target_type
            )
        return new_groups

        # 特殊人员替换特殊人员（按 ID 排序）
        admin_sp = sorted([sid for sid in people_from_admin if sid in pool_set])
        slot_sp = sorted({
            sid
            for dg, ng in groups.values()
            for sid in (dg + ng)
            if sid in pool_set
        })
        # 普通人员替换普通人员（按 ID 排序）
        admin_reg = []
        slot_reg = []

        # 先做特殊人员的 1:1 替换
        special_replacements: dict[int, int] = {}
        for i, old_sid in enumerate(slot_sp):
            if i < len(admin_sp):
                special_replacements[old_sid] = admin_sp[i]

        # 普通人员不要做“同位替换”，而是把两边的人交叉穿插，
        # 避免上一月行政班的普通人员被重新绑回同一对。
        mixed_regulars: list[int] = []
        max_len = max(len(admin_reg), len(slot_reg))
        for i in range(max_len):
            if i < len(admin_reg):
                mixed_regulars.append(admin_reg[i])
            if i < len(slot_reg):
                mixed_regulars.append(slot_reg[i])

        if not special_replacements:
            return groups

        # 在槽位分组中执行替换
        new_groups: dict[int, tuple[list[int], list[int]]] = {}
        for slot_idx in sorted(groups):
            dg, ng = groups[slot_idx]
            new_dg: list[int] = []
            new_ng: list[int] = []

            for sid in dg:
                new_dg.append(special_replacements.get(sid, sid))

            for sid in ng:
                new_ng.append(special_replacements.get(sid, sid))

            new_groups[slot_idx] = (new_dg, new_ng)

        return self._normalize_replaced_groups(new_groups, groups, sorted_ids)

    @staticmethod
    def _normalize_replaced_groups(
        new_groups: dict[int, tuple[list[int], list[int]]],
        original_groups: dict[int, tuple[list[int], list[int]]],
        candidates: list[int],
    ) -> dict[int, tuple[list[int], list[int]]]:
        candidate_pool = list(dict.fromkeys(candidates))
        candidate_set = set(candidate_pool)
        used: set[int] = set()
        normalized: dict[int, tuple[list[int], list[int]]] = {}

        def normalize_group(group: list[int], target_size: int) -> list[int]:
            result: list[int] = []
            for sid in group:
                if sid in candidate_set and sid not in used:
                    result.append(sid)
                    used.add(sid)
            for sid in candidate_pool:
                if len(result) >= target_size:
                    break
                if sid not in used:
                    result.append(sid)
                    used.add(sid)
            return result

        for slot_idx in sorted(new_groups):
            dg, ng = new_groups[slot_idx]
            orig_dg, orig_ng = original_groups.get(slot_idx, ([], []))
            normalized[slot_idx] = (
                normalize_group(dg, len(orig_dg)),
                normalize_group(ng, len(orig_ng)),
            )

        return normalized

    def _normalize_current_replaced_group(
        self,
        new_groups: dict[int, tuple[list[int], list[int]]],
        original_groups: dict[int, tuple[list[int], list[int]]],
        candidates: list[int],
        schedule_date: date,
        target_type: str,
    ) -> dict[int, tuple[list[int], list[int]]]:
        normalized = {
            slot_idx: (list(day_group), list(night_group))
            for slot_idx, (day_group, night_group) in new_groups.items()
        }
        if not normalized:
            return normalized

        n_slots = len(normalized)
        rotation_day = self.s._slot_rotation_day_index(schedule_date)
        slot_idx = rotation_day % n_slots
        rotation_number = rotation_day // n_slots
        use_day_group = (
            target_type == "day" if rotation_number % 2 == 0 else target_type == "night"
        )

        day_group, night_group = normalized.get(slot_idx, ([], []))
        orig_day, orig_night = original_groups.get(slot_idx, ([], []))
        candidate_pool = list(dict.fromkeys(candidates))
        candidate_set = set(candidate_pool)
        used = {
            sid
            for idx, (dg, ng) in normalized.items()
            if idx != slot_idx
            for sid in (dg + ng)
            if sid in candidate_set
        }

        def normalize_group(group: list[int], target_size: int) -> list[int]:
            result: list[int] = []
            for sid in group:
                if sid in candidate_set and sid not in used:
                    result.append(sid)
                    used.add(sid)
            for sid in candidate_pool:
                if len(result) >= target_size:
                    break
                if sid not in used:
                    result.append(sid)
                    used.add(sid)
            return result

        if use_day_group:
            normalized[slot_idx] = (
                normalize_group(day_group, len(orig_day)),
                night_group,
            )
        else:
            normalized[slot_idx] = (
                day_group,
                normalize_group(night_group, len(orig_night)),
            )

        return normalized

    def _fallback_select(
        self,
        candidates: list[int],
        date_str: str,
        target: int,
        is_night: bool,
    ) -> list[int]:
        """人数不足时的回退选择（公平排序）。"""
        dt = date.fromisoformat(date_str)
        combined = sorted(candidates, key=lambda sid: (
            self.s._night_shifts.get(sid, 0) + self.s._day_shifts.get(sid, 0),
            self.s._night_shifts.get(sid, 0) if is_night else self.s._day_shifts.get(sid, 0),
            sid,
        ))
        return combined[:target]

    @staticmethod
    def _pairings_to_groups(
        pairings: dict[tuple[int, str], tuple[list[int], list[bool]]],
    ) -> dict[int, tuple[list[int], list[int]]]:
        """将配对关系转换为槽位分组格式"""
        groups: dict[int, tuple[list[int], list[int]]] = {}
        for (slot_idx, group_type), (staff_ids, _) in pairings.items():
            if slot_idx not in groups:
                groups[slot_idx] = ([], [])
            if group_type == "day":
                groups[slot_idx] = (staff_ids, groups[slot_idx][1])
            else:
                groups[slot_idx] = (groups[slot_idx][0], staff_ids)
        return groups

    @staticmethod
    def _groups_to_pairings(
        groups: dict[int, tuple[list[int], list[int]]],
    ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
        """将槽位分组转换为配对关系格式"""
        pairings: dict[tuple[int, str], tuple[list[int], list[bool]]] = {}
        for slot_idx, (dg, ng) in groups.items():
            pairings[(slot_idx, "day")] = (dg, [False] * len(dg))
            pairings[(slot_idx, "night")] = (ng, [False] * len(ng))
        return pairings


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
        pre_history: dict[int, list[str]] | None = None,
        pairing_manager=None,
        prev_month_schedules=None,
        all_pairings=None,
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
        self._pre_history = pre_history or {}

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

        # 上月排班（按日期排序，供特殊人员跨月推导使用）
        self.prev_month_schedules: list = prev_month_schedules or []

        # 特殊人员跨月轮换缓存（shift_id -> selected_special_ids）
        self._prev_special_members: dict[int, list[int]] = {}

        # 本轮白班/夜班计数（用于平衡同类型班次分布）
        self._night_shifts: dict[int, int] = defaultdict(int)
        self._day_shifts: dict[int, int] = defaultdict(int)
        self._last_shift_type: dict[int, str] = {}
        self._last_shift_date: dict[int, str] = {}

        # 月轮班次已锁定人员（整月独占，不参与白夜班）
        self._active_month_key: int | None = None
        self._monthly_locked: set[int] = set()
        self._monthly_member_cache: dict[tuple[int, int], list[int]] = {}

        # 日轮绑定组：key=rotation_slot(0/1/2), value=(day_group, night_group)
        self._bound_groups: dict[int, tuple] = {}

        # 槽位分组器（跨月复用）
        self._slot_grouper = SlotGrouper(self.staff_map, self._is_new_employee)
        # 当天候选池缓存（白/夜班分开）
        self._day_candidates_cache: dict[str, list[int]] = {}
        # 从 DB 加载的配对关系
        self._loaded_pairings = all_pairings or {}
        # 需要保存的新配对
        self._new_pairings: dict[int, dict] = {}
        # 配对管理器
        self.pairing_manager = pairing_manager
        self._replacement_allowed_members: dict[int, set[int]] = {}
        self._replacement_groups_cache: dict[int, dict[int, tuple[list[int], list[int]]]] = {}
        self._replacement_processed_groups: set[tuple[int, int, str]] = set()
        self._replacement_used_members: set[int] = set()
        self._current_admin_members: dict[int, list[int]] = {}
        self._admin_replacement_map: dict[int, int] = {}
        self._current_special_locked: set[int] = set()
        self._special_source_shift_by_member: dict[int, int] = {}

        # 候选人过滤链
        self.candidate_filter = CandidateFilter(
            staff_special_rules=self.staff_special_rules,
            constraint_params=self.constraint_params,
            existing_details=existing_details,
            existing_schedules=existing_schedules,
            shift_templates=self.shift_templates,
            scorer=self.scorer,
            pre_history=self._pre_history,
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

    def _slot_rotation_day_index(self, schedule_date: date) -> int:
        anchor = getattr(self, "_slot_rotation_anchor_date", None)
        if not anchor:
            anchor = date(schedule_date.year, schedule_date.month, 1)
        return max(0, (schedule_date - anchor).days)

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
        history_dates = [
            schedule.date
            for schedule in self.existing_schedules
            if getattr(schedule, "org_id", org_id) == org_id
            and getattr(schedule, "date", None)
        ]
        self._slot_rotation_anchor_date = min(history_dates) if history_dates else start_date
        # 领导跨月偏移量（ISO 周号基准）
        self._leader_offsets: dict[int, int] = leader_offsets or {}

        # 初始化 SlotGrouper 月份状态（确保逐月/多月一致性）
        dt = date.fromisoformat(str(start_date))
        self._slot_grouper._current_month = dt.year * 12 + dt.month

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
                pool_added = 0
                for sid in shift.leader_pool:
                    if sid not in self.staff_map:
                        continue
                    self._all_leader_candidates.add(sid)
                    if sid not in available_ids:
                        available_ids.append(sid)
                        pool_added += 1
                self._diag_msgs.append(
                    f"[诊断-领导池] leader_pool={shift.leader_pool} "
                    f"in_staff_map={sum(1 for sid in shift.leader_pool if sid in self.staff_map)} "
                    f"added_to_available={pool_added}"
                )
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

        # 日轮通过 sorted(candidates)[:12] 自动排除周轮候选人，无需预锁定

        # 收集上月排班记录（special_pool 相同的班次之间交替轮换）
        sched_idx = {s.id: s for s in self.existing_schedules}
        if self.prev_month_schedules:
            self.prev_month_schedules = sorted(
                [s for s in self.prev_month_schedules if s.org_id == org_id],
                key=lambda s: getattr(s, "date", ""),
            )
        else:
            prev_month_end = start_date - timedelta(days=1)
            prev_month_start = date(prev_month_end.year, prev_month_end.month, 1)
            self.prev_month_schedules = sorted(
                [
                    s for s in self.existing_schedules
                    if s.org_id == org_id and prev_month_start <= s.date <= prev_month_end
                ],
                key=lambda s: getattr(s, "date", ""),
            )

        tail_start = start_date - timedelta(days=7)
        tail_start_str = str(tail_start)
        start_date_str = str(start_date)
        for d in self.existing_details:
            s = sched_idx.get(d.schedule_id)
            if not s:
                continue
            d_str = str(getattr(s, "date", ""))
            shift_t = self.shift_templates.get(getattr(s, "shift_id", None))
            if not shift_t:
                continue
            if tail_start_str <= d_str < start_date_str:
                is_night = self._is_night_shift(shift_t)
                self._last_shift_type[d.staff_id] = "night" if is_night else "day"
                self._last_shift_date[d.staff_id] = d_str

        current = start_date
        while current <= end_date:
            date_str = str(current)
            weekday = current.isoweekday()
            month_key = current.year * 12 + current.month
            if self._active_month_key != month_key:
                self._active_month_key = month_key
                self._monthly_locked.clear()
                self._current_admin_members.clear()
                self._current_special_locked.clear()
                self._day_candidates_cache.clear()
                self._replacement_groups_cache.clear()
                self._replacement_processed_groups.clear()
                self._replacement_used_members.clear()
                self._admin_replacement_map.clear()
                self._prepare_monthly_special_locks(strategy, active_shifts, available_ids, date_str)

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
                if is_monthly and result.member_ids:
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

    def _prepare_monthly_special_locks(
        self,
        strategy: IndividualStrategy,
        active_shifts: list[SchShiftTemplate],
        available_ids: list[int] | None = None,
        date_str: str | None = None,
    ) -> None:
        """Lock this month's admin roster before regular shifts are assigned."""
        for shift in active_shifts:
            if not shift.special_enabled:
                continue
            special_freq = shift.special_rotation_frequency or "month"
            member_freq = shift.member_rotation_frequency or "day"
            if special_freq != "month" and member_freq not in ("week", "month"):
                continue
            special_pool = sorted(shift.special_pool or [])
            if not special_pool:
                continue
            selected = strategy._derive_special_from_other_shifts(shift, special_pool)
            if selected is None:
                selected = special_pool[:shift.special_count]
            else:
                selected = list(dict.fromkeys(selected))[:shift.special_count]
            selected = [sid for sid in selected if sid in self.staff_map]
            if not selected:
                continue
            self._prev_special_members[shift.id] = selected
            self._current_special_locked.update(selected)
            admin_roster = list(selected)
            if available_ids is not None and date_str is not None:
                remaining_slots = max(0, shift.member_max - len(selected))
                if remaining_slots:
                    members, _ = strategy._assign_members(
                        shift,
                        date_str,
                        available_ids,
                        selected,
                        max_slots=remaining_slots,
                    )
                    admin_roster.extend(members)
            admin_roster = list(dict.fromkeys(admin_roster))
            if admin_roster:
                self._current_admin_members[shift.id] = admin_roster
                self._monthly_locked.update(
                    sid
                    for sid in admin_roster
                    if sid not in set(shift.special_pool or [])
                )

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
                    f"[诊断-领导] {shift.name} period={period} freq={leader_freq} "
                    f"leader_count_cfg={leader_count} full_count={full_count} "
                    f"filtered_count={len(candidates)} "
                    f"start_idx={start_idx} selected={selected} "
                    f"(共计{len(selected)}人)"
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
