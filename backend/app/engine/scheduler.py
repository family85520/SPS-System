"""自动排班算法引擎

核心规则（12人标准场景）：
1. 槽位分组：12人按ID排序，(day-1)%3分3槽，每槽4人(前2+后2)
2. 白夜交替：rotation偶数：前2白后2夜；奇数：前2夜后2白
3. 新老搭配：每组2人中1新员工+1老员工搭配
4. 整月绑定：同槽4人整月不变，不跨槽混打
5. 班次均衡：每人每月5白+5夜（30天月）
6. 跨月替换：特殊人员组变更时1对1替换对应槽位人员
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from app.engine.scoring import FairnessScorer
from app.models import OrgStaff
from app.models.constraint import SchConstraint
from app.models.shift_template import SchShiftTemplate
from app.models.special_rule import SchSpecialRule

logger = logging.getLogger("scheduler")


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
        self._run_start_str: str = "0000-01-01"

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

    def _filter_by_special_rules(
        self, candidates: list[int], date_str: str, shift_id: int,
    ) -> list[int]:
        return [sid for sid in candidates if not self._is_excluded_by_special_rules(sid, date_str, shift_id)]

    def _is_excluded_by_special_rules(
        self, staff_id: int, date_str: str, shift_id: int,
    ) -> bool:
        for rule in self._staff_special_rules.get(staff_id, []):
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

    def _filter_by_constraints(
        self, candidates: list[int], date_str: str, shift_id: int,
    ) -> list[int]:
        return [sid for sid in candidates if self._passes_constraints(sid, date_str, shift_id)]

    def _passes_constraints(self, staff_id: int, date_str: str, shift_id: int) -> bool:
        max_per_day = self._constraint_params.get("MAX_SHIFTS_PER_DAY", {}).get("count", 1)
        if self._count_today(staff_id, date_str) >= max_per_day:
            return False

        max_days = self._constraint_params.get("MAX_CONTINUOUS_DAYS", {}).get("max_days", 5)
        if self._will_exceed_continuous(staff_id, date_str, max_days):
            return False

        min_hours = self._constraint_params.get("MIN_SHIFT_INTERVAL", {}).get("hours", 8)
        if self._interval_violated(staff_id, date_str, shift_id, min_hours):
            return False

        return True

    def _count_today(self, staff_id: int, date_str: str) -> int:
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
        pre = self._pre_history.get(staff_id, [])
        if pre:
            all_dates_raw = sorted(set(all_dates_raw) | set(pre))
        run_start = getattr(self, '_run_start_str', '0000-01-01')
        effective_start = min(pre) if pre and min(pre) < run_start else run_start
        all_dates = [d for d in all_dates_raw if d >= effective_start]
        if date_str not in all_dates:
            all_dates.append(date_str)
            all_dates.sort()
        idx = all_dates.index(date_str)

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
    """12人标准槽位分组器

    规则：
    - 12人按ID排序，分3槽，每槽4人
    - 每槽前2人为一组（白班组/夜班组），后2人为一组
    - 新老搭配：每2人组中1新+1老
    - 整月绑定：同槽4人整月不变
    - 跨月1对1替换
    """

    def __init__(self, staff_map: dict[int, OrgStaff], is_new_employee_fn):
        self._staff_map = staff_map
        self._is_new = is_new_employee_fn
        # 当月绑定：slot_idx -> (day_group[2], night_group[2])
        self._month_groups: dict[int, tuple[list[int], list[int]]] = {}
        self._current_month: int = 0
        # 上月绑定（用于跨月替换）
        self._prev_month_groups: dict[int, tuple[list[int], list[int]]] = {}

    def get_month_groups(
        self,
        sorted_ids: list[int],
        year: int,
        month: int,
    ) -> dict[int, tuple[list[int], list[int]]]:
        """获取或构建指定月份的槽位绑定。

        如果已有绑定且人员未变，直接返回；
        如果人员有变更，执行跨月1对1替换；
        否则新建绑定。
        """
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
        """检查上月绑定是否可以复用（有人员变更时也可复用，由替换逻辑处理）。"""
        prev_all = set()
        for dg, ng in self._prev_month_groups.values():
            prev_all.update(dg)
            prev_all.update(ng)
        curr_all = set(sorted_ids)
        departed = prev_all - curr_all
        joined = curr_all - prev_all
        # 无变更：可复用
        if not departed and not joined:
            return True
        # 有变更且人数匹配：可复用（1:1替换）
        if len(departed) == len(joined) and len(departed) > 0:
            return True
        # 有变更但人数不匹配：也可复用（部分替换，剩余保持原位）
        if departed or joined:
            return True
        return False

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

        # 1对1替换（处理人数不匹配）
        replacements = dict(zip(departed, joined))
        new_groups = {}
        for slot_idx, (dg, ng) in self._prev_month_groups.items():
            # 替换离开的人，移除未被替换的离开人员
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
            # 找人数最少的槽位
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
        """构建新绑定：新老搭配 + 均匀分配到3槽。

        12人：每槽4人（2对），每对1新+1老
        其他人数：动态分配，尽量保持2人组结构
        """
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

        # 确定槽位数：标准12人=3槽，其他按比例
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
        self.s = scheduler

    @abstractmethod
    def assign(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        result: ScheduleResult,
        daily_assigned: set[int] | None = None,
    ) -> list[str]:
        ...


class IndividualStrategy(ScheduleStrategy):
    """逐人轮询排班（标准12人槽位轮转）。"""

    def assign(
        self, shift, date_str, available_ids, result, daily_assigned=None,
    ) -> list[str]:
        conflicts = []
        is_night = self.s._is_night_shift(shift)
        is_weekend = date.fromisoformat(date_str).isoweekday() >= 6
        daily = daily_assigned or set()

        if shift.leader_enabled and shift.leader_min > 0:
            leaders, lc = self.s._assign_leaders(shift, date_str, available_ids, is_night, is_weekend, daily)
            for lid in leaders:
                if lid not in result.leader_ids:
                    result.leader_ids.append(lid)
                result.member_ids.append(lid)
            conflicts.extend(lc)

        if shift.special_enabled:
            special_ids, sc = self._assign_special_group(shift, date_str, result.member_ids, daily)
            result.member_ids.extend(special_ids)
            conflicts.extend(sc)

        leader_set = set(result.leader_ids)
        already_non_leader = [sid for sid in result.member_ids if sid not in leader_set]
        remaining_slots = max(0, shift.member_max - len(already_non_leader))
        members, mc = self._assign_members(
            shift, date_str, available_ids, result.member_ids, max_slots=remaining_slots,
            daily_assigned=daily,
        )
        result.member_ids.extend(members)
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
        special_pool = sorted(shift.special_pool or [])  # 统一 ID 排序
        count = shift.special_count

        if not special_pool or not shift.special_enabled:
            return [], conflicts

        daily = daily_assigned or set()

        # 从其他班次的上月特殊人员推导
        new_members = self._derive_special_from_other_shifts(shift, special_pool, conflicts)

        if new_members is None:
            # 首次生成或无上月数据：按 ID 顺序选择
            if conflicts is not None:
                conflicts.append(f"[诊断] {shift.name}：无上月数据，使用默认顺序 special_pool[:count]={special_pool[:count]}")
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
            if sid not in self.s.staff_map:
                conflicts.append(f"{date_str} {shift.name}：特殊人员池中人员(ID:{sid})不在本组织中，已跳过")
                continue
            selected.append(sid)
            assigned_set.add(sid)

        if len(selected) < count:
            conflicts.append(f"{date_str} {shift.name}：特殊人员组可用人数不足，需{count}人，仅{len(selected)}人可用")

        # 保存当月特殊人员状态供后续推导使用
        self.s._prev_special_members[shift.id] = selected

        return selected, conflicts

    def _derive_special_from_other_shifts(
        self, current_shift: SchShiftTemplate, pool: list[int], conflicts: list[str] | None = None
    ) -> list[int] | None:
        """从上月其他班次推导本月特殊人员

        规则：特殊人员在不同班次间交替轮换。
        上月在白班/夜班的特殊人员，本月应在行政班；
        上月在行政班的特殊人员，本月应在白班/夜班。
        """
        pool_set = set(pool)
        count = current_shift.special_count

        # 从 prev_month_schedules 中找出所有其他班次的排班记录
        candidate_schedules = []
        for sched in self.s.prev_month_schedules:
            if sched.shift_id == current_shift.id:
                continue
            candidate_schedules.append(sched)

        if not candidate_schedules:
            if conflicts is not None:
                conflicts.append(f"[诊断] {current_shift.name}：上月无其他班次")
            return None

        # 按 shift_id 分组，每组取最后一天
        from collections import defaultdict
        by_shift: dict[int, list] = defaultdict(list)
        for sched in candidate_schedules:
            by_shift[sched.shift_id].append(sched)

        # 遍历所有其他班次，找到有 pool 人员的班次
        for other_shift_id in sorted(by_shift.keys()):
            schedules = by_shift[other_shift_id]
            last_sched = sorted(schedules, key=lambda s: str(getattr(s, "date", "")), reverse=True)[0]
            other_special = [
                d.staff_id
                for d in self.s.existing_details
                if d.schedule_id == last_sched.id and d.staff_id in pool_set
            ]
            if conflicts is not None:
                conflicts.append(f"[诊断] 其他班次shift_id={other_shift_id}, 最后一天={getattr(last_sched,'date','')}, pool人员={other_special}")
            if other_special:
                return other_special[:count]

        if conflicts is not None:
            conflicts.append(f"[诊断] {current_shift.name}：所有其他班次均无特殊人员明细")
        return None

    def _derive_prev_special_from_db(self, shift: SchShiftTemplate) -> list[int] | None:
        """从内存缓存读取上月特殊人员（由 _assign_special_group 保存）"""
        return self.s._prev_special_members.get(shift.id, None) or None

    def _rotate_special(self, shift: SchShiftTemplate, prev_special: list[int], pool: list[int]) -> list[int]:
        """特殊人员轮换：交替班次

        根据设计规则：特殊人员在两个班次间交替轮换。
        如果上月特殊人员是 pool 中的第 N 个，本月应该用下一个。
        """
        pool_sorted = sorted(pool)
        count = shift.special_count

        if not prev_special:
            return pool_sorted[:count]

        # 找到上月特殊人员在池中的位置
        # 使用第一个特殊人员的位置来确定轮换
        if prev_special[0] in pool_sorted:
            last_idx = pool_sorted.index(prev_special[0])
            # 轮换到下一个位置
            next_idx = (last_idx + count) % len(pool_sorted)
            result = []
            for i in range(count):
                idx = (next_idx + i) % len(pool_sorted)
                result.append(pool_sorted[idx])
            return result

        # 如果上月特殊人员不在池中，使用默认顺序
        return pool_sorted[:count]

    def _assign_members(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        already_assigned: list[int],
        max_slots: int | None = None,
        daily_assigned: set[int] | None = None,
    ) -> tuple[list[int], list[str]]:
        conflicts: list[str] = []
        daily = daily_assigned or set()
        excluded = set(already_assigned) | daily  # 排除当天已排班的人

        # 始终排除领导候选人（无论当前班次是否启用领导组）
        leader_candidates = getattr(self.s, '_all_leader_candidates', None)
        if leader_candidates:
            excluded |= leader_candidates

        is_monthly = (shift.member_rotation_frequency or 'day') in ('week', 'month')
        if not is_monthly and self.s._monthly_locked:
            excluded |= self.s._monthly_locked

        freq = shift.member_rotation_frequency or 'day'

        # 排除当月被选为特殊人员的人（无论当天是否有特殊班次）
        # 特殊人员整月固定在特殊班次，不应出现在普通班次
        if not shift.special_enabled:
            for other_shift in self.s.shift_templates.values():
                if other_shift.special_enabled:
                    prev_special = self.s._prev_special_members.get(other_shift.id, [])
                    excluded |= set(prev_special)

        # 日轮班次：使用不含 daily_assigned 的候选池构建槽位分组
        if freq == 'day':
            slot_excluded = set(already_assigned)
            if leader_candidates:
                slot_excluded |= leader_candidates
            if not is_monthly and self.s._monthly_locked:
                slot_excluded |= self.s._monthly_locked
            # 同样排除当月特殊人员
            if not shift.special_enabled:
                for other_shift in self.s.shift_templates.values():
                    if other_shift.special_enabled:
                        prev_special = self.s._prev_special_members.get(other_shift.id, [])
                        slot_excluded |= set(prev_special)
            slot_candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, slot_excluded)
        else:
            slot_candidates = None

        # 跨月交叉替换：将上月行政班的非special人员添加到当前候选池
        # 在槽位分组创建之前注入，让SlotGrouper正确处理
        if self.s.prev_month_schedules and not shift.special_enabled:
            injected = self._get_cross_month_injections(shift)
            if injected:
                for sid in injected:
                    if sid in self.s.staff_map and sid not in available_ids:
                        available_ids.append(sid)
                # 标记需要重建分组，因为注入了新的人员
                self.s._need_rebuild_groups[shift.id] = True
                # 重新计算slot_candidates和candidates（包含注入的人员）
                if freq == 'day' and slot_candidates is not None:
                    slot_candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, slot_excluded)
                candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, excluded)
                if max_slots is None:
                    max_slots = shift.member_max
                target = min(max_slots, len(candidates))

        candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, excluded)

        if max_slots is None:
            max_slots = shift.member_max
        target = min(max_slots, len(candidates))

        if len(candidates) < shift.member_min:
            conflicts.append(
                f"{date_str} {shift.name}：可用人员不足，最少需{shift.member_min}人，仅{len(candidates)}人可用"
            )

        if target <= 0 or not candidates:
            return [], conflicts

        if freq == 'day':
            # 日轮：用不含 daily_assigned 的候选池构建槽位，再从结果中过滤
            selected = self._slot_rotate_select(slot_candidates, date_str, target, shift)
            # 过滤掉当天已排班的人
            selected = [sid for sid in selected if sid not in daily]
            # 截断到目标人数
            selected = selected[:target]
        else:
            # 周轮/月轮：纯数学偏移
            period = self.s._get_rotation_period(date_str, freq)
            stable_sorted = sorted(candidates)
            n = len(stable_sorted)
            start = (period * target) % n
            selected = [stable_sorted[(start + i) % n] for i in range(target)]

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

        重要：优先使用数据库中的配对关系，没有则用 SlotGrouper 生成。
        """
        is_night = self.s._is_night_shift(shift)
        target_type = "night" if is_night else "day"

        dt = date.fromisoformat(date_str)
        year, month = dt.year, dt.month
        n_total = len(candidates)

        # 跨月重置
        if self.s._slot_grouper._current_month != year * 12 + month:
            self.s._monthly_locked.clear()
            self.s._day_candidates_cache.clear()

        # 跨月原位替换: 有上月数据时，在上月分组中执行替换
        if self.s.prev_month_schedules and self.s._loaded_pairings.get(shift.id):
            groups = self._pairings_to_groups(self.s._loaded_pairings[shift.id])
            groups = self._apply_in_place_replacement(groups, shift)
        else:
            # 当天候选池缓存：白班/夜班使用相同的候选池
            cache_key = date_str
            if cache_key not in self.s._day_candidates_cache:
                self.s._day_candidates_cache[cache_key] = sorted(candidates)
            sorted_ids = self.s._day_candidates_cache[cache_key]
            groups = self.s._slot_grouper.get_month_groups(sorted_ids, year, month)

            # 首次生成时，保存配对关系供后续使用
            if groups and shift.id not in self.s._new_pairings:
                self.s._new_pairings[shift.id] = self._groups_to_pairings(groups)

        if not groups:
            # 人数不足时回退到公平排序
            return self._fallback_select(candidates, date_str, target, is_night)

        # 标准12人场景：3槽位
        n_slots = len(groups)
        if n_slots == 0:
            return self._fallback_select(candidates, date_str, target, is_night)

        # 选择槽位：(day-1)%3
        rotation_slot = (dt.day - 1) % n_slots
        # 白夜方向：rotation_number%2
        rotation_number = (dt.day - 1) // n_slots

        dg, ng = groups[rotation_slot]

        if rotation_number % 2 == 0:
            # 偶数轮：前半白，后半夜
            selected = (dg if target_type == "day" else ng)
        else:
            # 奇数轮：前半夜，后半白
            selected = (ng if target_type == "day" else dg)

        # 过滤掉不在当前候选集中的人（处理 daily_assigned 排除）
        candidate_set = set(candidates)
        selected = [sid for sid in selected if sid in candidate_set]

        # 不截断，返回整个组（白班/夜班共享同一槽位）
        return selected

    def _get_cross_month_injections(
        self,
        shift: SchShiftTemplate,
    ) -> list[int]:
        """获取跨月需要注入的人员列表。

        规则：上月行政班的普通人员（非 special_pool）本月应去白班/夜班。
        上月白班/夜班的普通人员（非 special_pool）本月应去行政班。
        返回需要注入到当前班次的非特殊人员ID列表（按ID排序）。
        """
        if not self.s.prev_month_schedules:
            return []

        pool_set = set(shift.special_pool or [])

        # 找到行政班（special_enabled 的班次）
        admin_shift = None
        for sid, s in self.s.shift_templates.items():
            if s.special_enabled:
                admin_shift = s
                break

        if not admin_shift:
            return []

        # 确定当前班次是否是行政班
        is_admin = (admin_shift.id == shift.id)

        # 收集上月行政班和白班/夜班的普通人员
        admin_regular = []  # 行政班的普通人员
        slot_regular = []   # 白班/夜班的普通人员

        # 行政班所有人员
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == admin_shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id and d.staff_id not in pool_set:
                        if d.staff_id not in admin_regular:
                            admin_regular.append(d.staff_id)
                break

        # 白班/夜班所有人员（排除行政班）
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id != admin_shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id and d.staff_id not in pool_set:
                        if d.staff_id not in slot_regular:
                            slot_regular.append(d.staff_id)
                break

        # 跨月轮换规则：
        # 行政班的普通人员 -> 白班/夜班
        # 白班/夜班的普通人员 -> 行政班
        if is_admin:
            # 当前是行政班，注入白班/夜班的普通人员
            return sorted(slot_regular)
        else:
            # 当前是白班/夜班，注入行政班的普通人员
            return sorted(admin_regular)

    def _get_current_admin_members(self) -> list[int]:
        """获取本月行政班已分配的人员列表"""
        admin_shift = None
        for sid, s in self.s.shift_templates.items():
            if s.special_enabled:
                admin_shift = s
                break
        if not admin_shift:
            return []
        # 从 _prev_special_members 中获取行政班特殊人员
        admin_sp = self.s._prev_special_members.get(admin_shift.id, [])
        return admin_sp

    def _apply_in_place_replacement(
        self,
        groups: dict[int, tuple[list[int], list[int]]],
        shift: SchShiftTemplate,
    ) -> dict[int, tuple[list[int], list[int]]]:
        """跨月原位替换：在上月分组中直接替换人员。

        规则：
        1. 特殊人员：上月行政班的特殊人员 -> 本月白班/夜班（替换上月白班/夜班的特殊人员）
        2. 普通人员：上月行政班的普通人员 -> 本月白班/夜班（替换上月白班/夜班的普通人员）
        3. 按 ID 排序后一一对应替换
        """
        if not groups or not self.s.prev_month_schedules:
            return groups

        pool_set = set(shift.special_pool or [])

        # 找到行政班
        admin_shift = None
        for sid, s in self.s.shift_templates.items():
            if s.special_enabled:
                admin_shift = s
                break
        if not admin_shift or admin_shift.id == shift.id:
            return groups

        # 上月行政班人员（取第一天，本月应去白班/夜班）
        people_from_admin = []
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == admin_shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id:
                        if d.staff_id not in people_from_admin:
                            people_from_admin.append(d.staff_id)
                break

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

        # 特殊人员替换特殊人员（按 ID 排序）
        admin_sp = sorted([sid for sid in people_from_admin if sid in pool_set])
        slot_sp = sorted([sid for sid in people_from_slot if sid in pool_set])

        # 普通人员替换普通人员（按 ID 排序）
        admin_reg = sorted([sid for sid in people_from_admin if sid not in pool_set])
        slot_reg = sorted([sid for sid in people_from_slot if sid not in pool_set])

        # 构建替换映射
        replacements = {}
        for i, old_sid in enumerate(slot_sp):
            if i < len(admin_sp):
                replacements[old_sid] = admin_sp[i]
        for i, old_sid in enumerate(slot_reg):
            if i < len(admin_reg):
                replacements[old_sid] = admin_reg[i]

        if not replacements:
            return groups

        # 在槽位分组中执行替换
        new_groups = {}
        for slot_idx, (dg, ng) in groups.items():
            new_dg = [replacements.get(sid, sid) for sid in dg]
            new_ng = [replacements.get(sid, sid) for sid in ng]
            new_groups[slot_idx] = (new_dg, new_ng)

        return new_groups

    def _apply_special_replacement_to_groups(
        self,
        groups: dict[int, tuple[list[int], list[int]]],
        shift: SchShiftTemplate,
        candidates: list[int],
    ) -> dict[int, tuple[list[int], list[int]]]:
        """跨月原位替换：按 ID 排序后一一对应替换。

        规则：
        1. 特殊人员替换特殊人员（按 ID 排序对应）
        2. 普通人员替换普通人员（按 ID 排序对应）
        3. 行政班人员 ↔ 白班/夜班人员交叉替换
        """
        if not groups or not self.s.prev_month_schedules:
            return groups

        # 收集特殊人员池
        special_pool = set()
        for sid, s in self.s.shift_templates.items():
            if s.special_enabled and s.special_pool:
                special_pool.update(s.special_pool)

        if not special_pool:
            return groups

        # 收集上月行政班所有人员
        admin_shift = None
        for sid, s in self.s.shift_templates.items():
            if s.special_enabled:
                admin_shift = s
                break

        if not admin_shift:
            return groups

        # 上月行政班人员（取第一天数据）
        admin_sp = []  # 特殊人员
        admin_reg = []  # 普通人员
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == admin_shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id:
                        if d.staff_id in special_pool:
                            if d.staff_id not in admin_sp:
                                admin_sp.append(d.staff_id)
                        else:
                            if d.staff_id not in admin_reg:
                                admin_reg.append(d.staff_id)
                break  # 只取第一天

        # 上月白班/夜班槽位中的人员（取第一天数据）
        slot_sp = []  # 特殊人员
        slot_reg = []  # 普通人员
        for sched in sorted(self.s.prev_month_schedules, key=lambda x: x.date):
            if sched.shift_id == shift.id:
                for d in self.s.existing_details:
                    if d.schedule_id == sched.id:
                        if d.staff_id in special_pool:
                            if d.staff_id not in slot_sp:
                                slot_sp.append(d.staff_id)
                        else:
                            if d.staff_id not in slot_reg:
                                slot_reg.append(d.staff_id)
                break  # 只取第一天

        if not admin_sp and not admin_reg:
            return groups

        # 按 ID 排序
        admin_sp.sort()
        admin_reg.sort()
        slot_sp.sort()
        slot_reg.sort()

        # 构建替换映射
        replacements = {}
        # 特殊人员：把slot中的旧特殊人员替换为admin中的新特殊人员
        for i, old_sid in enumerate(slot_sp):
            if i < len(admin_sp):
                replacements[old_sid] = admin_sp[i]
        # 普通人员：把slot中的旧普通人员替换为admin中的新普通人员
        for i, old_sid in enumerate(slot_reg):
            if i < len(admin_reg):
                replacements[old_sid] = admin_reg[i]

        if not replacements:
            return groups

        # 在槽位中执行替换
        new_groups = {}
        for slot_idx, (dg, ng) in groups.items():
            new_dg = [replacements.get(sid, sid) for sid in dg]
            new_ng = [replacements.get(sid, sid) for sid in ng]
            new_groups[slot_idx] = (new_dg, new_ng)

        return new_groups

    def _fallback_select(
        self,
        candidates: list[int],
        date_str: str,
        target: int,
        is_night: bool,
    ) -> list[int]:
        """人数不足时的回退选择（公平排序）。"""
        dt = date.fromisoformat(date_str)
        day_seed = dt.day + dt.month * 31
        combined = sorted(candidates, key=lambda sid: (
            self.s._night_shifts.get(sid, 0) + self.s._day_shifts.get(sid, 0),
            self.s._night_shifts.get(sid, 0) if is_night else self.s._day_shifts.get(sid, 0),
            (sid * day_seed) % 997,
        ))
        return combined[:target]

    @staticmethod
    def _pairings_to_groups(
        pairings: dict[tuple[int, str], tuple[list[int], list[bool]]],
    ) -> dict[int, tuple[list[int], list[int]]]:
        """将配对关系转换为槽位分组格式"""
        groups: dict[int, tuple[list[int], list[int]]] = {}
        for (slot_idx, group_type), (staff_ids, is_new) in pairings.items():
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
    - 执行槽位轮转排班策略
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
        pairing_manager=None,  # 新增：配对管理器
        prev_month_schedules=None,  # 新增：上月排班记录
        all_pairings=None,  # 新增：配对关系缓存
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
        self.pairing_manager = pairing_manager
        self.prev_month_schedules = prev_month_schedules or []
        self._loaded_pairings = all_pairings or {}  # {shift_id: {(slot_idx, group_type): (staff_ids, is_new)}}
        self._new_pairings: dict[int, dict[tuple[int, str], tuple[list[int], list[bool]]]] = {}  # 需要保存的新配对
        self._need_rebuild_groups: dict[int, bool] = {}  # 跨月注入时需要重建分组

        self.staff_map: dict[int, OrgStaff] = {s.id: s for s in staff_list}
        self.staff_ids: list[int] = [s.id for s in staff_list]

        self.constraint_params: dict[str, dict] = {
            c.rule_type: c.params or {} for c in self.constraints
        }

        self.staff_special_rules: dict[int, list[SchSpecialRule]] = defaultdict(list)
        for r in special_rules:
            self.staff_special_rules[r.staff_id].append(r)

        fairness_weights = self.constraint_params.get("FAIRNESS_WEIGHTS", {})
        self.scorer = FairnessScorer(
            existing_schedules, existing_details, self.shift_templates,
            weights=fairness_weights if fairness_weights else None,
        )

        self._initial_shift_counts: dict[int, int] = {
            sid: len(self.scorer.staff_days.get(sid, set())) for sid in self.staff_ids
        }

        self._diag_msgs: list[str] = []

        self._night_shifts: dict[int, int] = defaultdict(int)
        self._day_shifts: dict[int, int] = defaultdict(int)

        self._monthly_locked: set[int] = set()
        self._day_candidates_cache: dict[str, list[int]] = {}  # 当天候选池缓存

        # 特殊人员组跨月替换状态
        self._prev_special_members: dict[int, list[int]] = {}  # shift_id -> [staff_id, ...]
        self._special_current_month: int = 0

        # 槽位分组器
        self._slot_grouper = SlotGrouper(self.staff_map, self._is_new_employee)

        # 配对关系缓存：shift_id -> {(slot_idx, group_type): (staff_ids, is_new)}
        self._pairings_cache: dict[int, dict[tuple[int, str], tuple[list[int], list[bool]]]] = {}
        self._pairings_dirty: dict[int, bool] = {}  # 标记哪些班次的配对需要保存

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
        if "新员工" in self.staff_tag_roles_map.get(staff_id, []):
            return True
        staff = self.staff_map.get(staff_id)
        if staff and staff.tags and "新员工" in (staff.tags or []):
            return True
        return False

    def _get_rotation_period(self, date_str: str, freq: str) -> int:
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
        results: list[ScheduleResult] = []
        all_conflicts: list[str] = []

        self._rotation_start_date = start_date
        self._leader_offsets: dict[int, int] = leader_offsets or {}

        available_ids = [
            s.id for s in self.staff_list
            if s.id in staff_ids and s.status == 1
        ]

        active_shifts = [
            self.shift_templates[sid]
            for sid in shift_template_ids
            if sid in self.shift_templates and self.shift_templates[sid].status == 1
        ]

        for shift in active_shifts:
            if shift.special_enabled:
                for sid in (shift.special_pool or []):
                    if sid in self.staff_map and sid not in available_ids:
                        available_ids.append(sid)

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
                tag_name = getattr(shift, 'leader_tag_name', None) or '领导'
                for s in self.staff_list:
                    sid = s.id
                    old_has = bool(s.tags and tag_name in (s.tags or []))
                    new_has = tag_name in self.staff_tag_roles_map.get(sid, [])
                    if (old_has or new_has) and s.status == 1:
                        self._all_leader_candidates.add(sid)
                        if sid not in available_ids:
                            available_ids.append(sid)

        active_shifts.sort(key=lambda s: (
            0 if (s.member_rotation_frequency or 'day') in ('week', 'month') else 1
        ))

        all_constraint_map = {c.id: c for c in self.constraints}

        total_staff = len(available_ids)
        daily_max_count = None
        if self.org_max_ratio and total_staff > 0:
            daily_max_count = max(1, int(total_staff * self.org_max_ratio))

        strategy = IndividualStrategy(self)
        self.candidate_filter._run_start_str = str(start_date)

        tail_start = start_date - timedelta(days=7)
        tail_start_str = str(tail_start)
        start_date_str = str(start_date)
        sched_idx = {s.id: s for s in self.existing_schedules}
        for d in self.existing_details:
            s = sched_idx.get(d.schedule_id)
            if not s:
                continue
            d_str = str(getattr(s, "date", ""))
            if tail_start_str <= d_str < start_date_str:
                shift_t = self.shift_templates.get(getattr(s, "shift_id", None))
                if shift_t:
                    self.scorer.staff_last_shift_type[d.staff_id] = (
                        "night" if self._is_night_shift(shift_t) else "day"
                    )

        current = start_date
        while current <= end_date:
            date_str = str(current)
            weekday = current.isoweekday()
            daily_assigned: set[int] = set()  # 当天已排班人员（跨班次共享）

            for shift in active_shifts:
                if weekday not in (shift.apply_days or [1, 2, 3, 4, 5, 6, 7]):
                    continue

                template_constraint_ids = shift.constraint_ids
                if template_constraint_ids:
                    template_constraints = [
                        all_constraint_map[cid]
                        for cid in template_constraint_ids
                        if cid in all_constraint_map
                    ]
                else:
                    template_constraints = self.constraints
                orig_constraint_params = self.candidate_filter._constraint_params
                self.candidate_filter._constraint_params = {
                    c.rule_type: c.params or {} for c in template_constraints
                }

                result = ScheduleResult(date_str, shift.id, org_id)
                conflicts = strategy.assign(
                    shift, date_str, available_ids, result, daily_assigned,
                )
                result.conflicts.extend(conflicts)
                all_conflicts.extend(conflicts)

                self.candidate_filter._constraint_params = orig_constraint_params

                result.member_ids = list(dict.fromkeys(result.member_ids))

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

                for sid in result.member_ids:
                    self.scorer.record_assignment(sid, date_str, shift.id)
                    daily_assigned.add(sid)  # 记录当天已排班

                if self._is_night_shift(shift):
                    for sid in result.member_ids:
                        self._night_shifts[sid] += 1
                else:
                    for sid in result.member_ids:
                        self._day_shifts[sid] += 1

                result.member_ids = self._truncate_members(result, shift)

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
        daily_assigned: set[int] | None = None,
    ) -> tuple[list[int], list[str]]:
        conflicts: list[str] = []
        daily = daily_assigned or set()

        if shift.leader_pool:
            candidates = [sid for sid in shift.leader_pool if sid in available_ids and sid not in daily]
        else:
            tagged = []
            tag_name = getattr(shift, 'leader_tag_name', None) or '领导'
            for s in self.staff_list:
                if s.id not in available_ids or s.id in daily:
                    continue
                old_has = bool(s.tags and tag_name in (s.tags or []))
                new_has = tag_name in self.staff_tag_roles_map.get(s.id, [])
                if old_has or new_has:
                    tagged.append(s.id)
            candidates = tagged

        full_pool = list(candidates)

        candidates = self.candidate_filter._filter_by_special_rules(
            list(candidates), date_str, shift.id
        )
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

        if leader_freq in ("week", "month"):
            if leader_freq == "week":
                iso_week = date.fromisoformat(date_str).isocalendar()[1]
                leader_offset = self._leader_offsets.get(shift.id, iso_week)
                period = iso_week - leader_offset
            else:
                period = self._get_rotation_period(date_str, leader_freq)

            full_sorted = sorted(full_pool)
            full_count = max(1, len(full_sorted))
            start_idx = (period * leader_count) % full_count
            filtered_set = set(candidates)
            selected = []
            for i in range(full_count):
                idx = (start_idx + i) % full_count
                sid = full_sorted[idx]
                if sid in filtered_set and sid not in selected:
                    selected.append(sid)
                if len(selected) >= leader_count:
                    break
        else:
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
    #  工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _truncate_members(result: ScheduleResult, shift: SchShiftTemplate) -> list[int]:
        """截断成员列表，但保留特殊人员和槽位绑定选出的人员。"""
        members = result.member_ids
        leader_set = set(result.leader_ids)
        leader_part = [lid for lid in members if lid in leader_set]
        non_leader = [mid for mid in members if mid not in leader_set]

        special_ids: set[int] = set()
        if shift.special_enabled:
            special_ids = set(shift.special_pool or [])

        special_in = [mid for mid in non_leader if mid in special_ids]
        regular_in = [mid for mid in non_leader if mid not in special_ids]

        leader_cap = max(shift.leader_max, shift.leader_count, len(leader_part))
        effective_max = leader_cap + shift.member_max + len(special_in)

        # 只在超出上限时截断，且保留特殊人员
        if len(members) > effective_max:
            # 不截断普通成员（槽位绑定已保证公平分配）
            return leader_part[:leader_cap] + special_in + regular_in

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
