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

    __slots__ = ("date", "shift_id", "org_id", "leader_id", "member_ids", "conflicts")

    def __init__(self, date_str: str, shift_id: int, org_id: int):
        self.date = date_str
        self.shift_id = shift_id
        self.org_id = org_id
        self.leader_id: Optional[int] = None
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
        all_dates = sorted(self._scorer.staff_days.get(staff_id, set()))
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
#  排班策略（策略模式）
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
        team_map: dict[int, list],
        include_leader: bool,
    ) -> list[str]:
        """执行排班，返回冲突列表。"""
        ...


class IndividualStrategy(ScheduleStrategy):
    """模式一：逐人轮询。"""

    def assign(
        self, shift, date_str, available_ids, result, team_map, include_leader,
    ) -> list[str]:
        conflicts = []
        is_night = self.s._is_night_shift(shift)
        is_weekend = date.fromisoformat(date_str).isoweekday() >= 6

        # 排领导
        if include_leader and shift.leader_min > 0:
            leaders, lc = self.s._assign_leaders(shift, date_str, available_ids, is_night, is_weekend)
            for lid in leaders:
                result.leader_id = result.leader_id or lid
                result.member_ids.append(lid)
            conflicts.extend(lc)

        # 排成员
        members, mc = self._assign_members(shift, date_str, available_ids, result.member_ids)
        result.member_ids.extend(members)
        conflicts.extend(mc)
        return conflicts

    def _assign_members(
        self,
        shift: SchShiftTemplate,
        date_str: str,
        available_ids: list[int],
        already_assigned: list[int],
    ) -> tuple[list[int], list[str]]:
        conflicts: list[str] = []
        candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, set(already_assigned))

        target = min(shift.member_max, len(candidates))
        if len(candidates) < shift.member_min:
            conflicts.append(
                f"{date_str} {shift.name}：可用人员不足，最少需{shift.member_min}人，仅{len(candidates)}人可用"
            )

        if target <= 0 or not candidates:
            return [], conflicts

        selected = self.s._tier_rotate_select(candidates, date_str, target)
        return selected, conflicts


class TeamRotationStrategy(ScheduleStrategy):
    """模式二：值班组轮换。"""

    def assign(
        self, shift, date_str, available_ids, result, team_map, include_leader,
    ) -> list[str]:
        conflicts = []
        teams = team_map.get(shift.id, [])

        if not teams:
            conflicts.append(f"{date_str} {shift.name}：未配置值班组，无法使用值班组轮换模式")
            return conflicts

        valid_teams = self._filter_valid_teams(teams, available_ids)
        if not valid_teams:
            conflicts.append(f"{date_str} {shift.name}：所有值班组均无可用人员")
            return conflicts

        # 按日期轮转选取
        day_index = (date.fromisoformat(date_str) - date(date.fromisoformat(date_str).year, 1, 1)).days
        selected_team, team_staff = valid_teams[day_index % len(valid_teams)]

        # 组内排领导
        if shift.leader_min > 0:
            leader_cands = [sid for sid in team_staff if sid in available_ids]
            if leader_cands:
                count_map = {sid: len(self.s.scorer.staff_days.get(sid, set())) for sid in leader_cands}
                leader_cands.sort(key=lambda sid: count_map[sid])
                for lid in leader_cands[: shift.leader_min]:
                    result.leader_id = result.leader_id or lid
                    result.member_ids.append(lid)

        # 组内排成员
        for sid in team_staff:
            if sid in available_ids and sid not in result.member_ids:
                result.member_ids.append(sid)

        return conflicts

    @staticmethod
    def _filter_valid_teams(teams: list, available_ids: list[int]) -> list[tuple]:
        valid = []
        for team in teams:
            staff = json.loads(team.staff_ids) if isinstance(team.staff_ids, str) else (team.staff_ids or [])
            available_in = [sid for sid in staff if sid in available_ids]
            if available_in:
                valid.append((team, staff))
        return valid


class RotationGroupStrategy(ScheduleStrategy):
    """模式三：轮换组排班。"""

    def assign(
        self, shift, date_str, available_ids, result, team_map, include_leader,
    ) -> list[str]:
        conflicts = []
        is_night = self.s._is_night_shift(shift)
        is_weekend = date.fromisoformat(date_str).isoweekday() >= 6

        # 先分配轮换组固定人员
        fixed = self._resolve_rotation_groups(shift, date_str)
        selected: list[int] = []
        for fid in fixed:
            if fid in available_ids and fid not in set(result.member_ids):
                selected.append(fid)
            elif fid not in available_ids:
                conflicts.append(f"{date_str} {shift.name}：轮换组指定人员(ID:{fid})不在可用人员中")

        # 补充剩余位置
        excluded = set(result.member_ids) | set(selected)
        candidates = self.s.candidate_filter.apply(available_ids, date_str, shift.id, excluded)
        remaining_slots = shift.member_max - len(selected)

        if remaining_slots > 0 and candidates:
            dt_obj = date.fromisoformat(date_str)
            rotation_freq = getattr(shift, "rotation_frequency", "day")
            period_index = self._period_key(dt_obj, rotation_freq)
            count_map = {sid: len(self.s.scorer.staff_days.get(sid, set())) for sid in candidates}
            candidates_sorted = sorted(candidates, key=lambda sid: (count_map[sid], sid))
            total = len(candidates_sorted)
            start = (period_index * remaining_slots) % total
            rotated = candidates_sorted[start:] + candidates_sorted[:start]
            selected.extend(rotated[:remaining_slots])

        result.member_ids.extend(selected)
        return conflicts

    @staticmethod
    def _resolve_rotation_groups(shift: SchShiftTemplate, date_str: str) -> list[int]:
        rotation_groups = getattr(shift, "rotation_groups_list", None)
        if not rotation_groups:
            return []

        dt_obj = date.fromisoformat(date_str)
        groups = sorted(
            [g for g in rotation_groups if g.enabled], key=lambda g: g.priority
        )

        fixed_ids: list[int] = []
        for group in groups:
            staff_ids = json.loads(group.staff_ids) if isinstance(group.staff_ids, str) else (group.staff_ids or [])
            if not staff_ids:
                continue

            unit = group.rotation_unit
            if unit == "day":
                index = dt_obj.timetuple().tm_yday % len(staff_ids)
            elif unit == "week":
                index = dt_obj.isocalendar()[1] % len(staff_ids)
            elif unit == "month":
                index = (dt_obj.year * 12 + dt_obj.month) % len(staff_ids)
            else:
                index = 0

            for i in range(group.slot_count):
                selected = staff_ids[(index + i) % len(staff_ids)]
                if selected not in fixed_ids:
                    fixed_ids.append(selected)

        return fixed_ids

    @staticmethod
    def _period_key(dt_obj: date, freq: str) -> int:
        if freq == "week":
            return dt_obj.isocalendar()[1]
        if freq == "month":
            return dt_obj.year * 12 + dt_obj.month
        return dt_obj.timetuple().tm_yday


# ====================================================================== #
#  自动排班引擎
# ====================================================================== #

class AutoScheduler:
    """自动排班引擎

    核心职责：
    - 按天遍历、按班次遍历
    - 委托具体策略执行排班
    - 维护公平性打分器状态
    - 生成报告
    """

    # 策略注册表
    _STRATEGY_MAP: dict[str, type[ScheduleStrategy]] = {
        "individual": IndividualStrategy,
        "team_rotation": TeamRotationStrategy,
        "rotation_group": RotationGroupStrategy,
    }

    def __init__(
        self,
        staff_list: list[OrgStaff],
        shift_templates: list[SchShiftTemplate],
        constraints: list[SchConstraint],
        special_rules: list[SchSpecialRule],
        existing_schedules: list,
        existing_details: list,
    ):
        self.staff_list = staff_list
        self.shift_templates: dict[int, SchShiftTemplate] = {s.id: s for s in shift_templates}
        self.constraints = sorted(
            [c for c in constraints if c.enabled], key=lambda x: x.priority or 999
        )
        self.existing_schedules = existing_schedules
        self.existing_details = existing_details

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

    def generate(
        self,
        start_date: date,
        end_date: date,
        org_id: int,
        shift_template_ids: list[int],
        staff_ids: list[int],
        include_leader: bool = True,
    ) -> dict:
        """生成排班表。"""
        results: list[ScheduleResult] = []
        all_conflicts: list[str] = []

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

        # 构建值班组索引
        team_map = {shift.id: self._build_team_list(shift) for shift in active_shifts}

        # 按天 → 按班次 循环
        current = start_date
        while current <= end_date:
            date_str = str(current)
            weekday = current.isoweekday()

            for shift in active_shifts:
                if weekday not in (shift.apply_days or [1, 2, 3, 4, 5, 6, 7]):
                    continue

                result = ScheduleResult(date_str, shift.id, org_id)
                schedule_mode = getattr(shift, "schedule_mode", "individual")

                # 委托策略
                strategy_cls = self._STRATEGY_MAP.get(schedule_mode, IndividualStrategy)
                strategy = strategy_cls(self)
                conflicts = strategy.assign(
                    shift, date_str, available_ids, result, team_map, include_leader,
                )
                result.conflicts.extend(conflicts)
                all_conflicts.extend(conflicts)

                # 去重
                result.member_ids = list(dict.fromkeys(result.member_ids))

                # 记录到打分器
                for sid in result.member_ids:
                    self.scorer.record_assignment(sid, date_str, shift.id)

                # 兜底截断
                result.member_ids = self._truncate_members(result, shift)
                results.append(result)

            current += timedelta(days=1)

        report = self._build_report(results)
        return {"schedules": results, "report": report, "conflicts": all_conflicts}

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

        # 确定候选池
        if shift.leader_pool:
            candidates = [sid for sid in shift.leader_pool if sid in available_ids]
        else:
            tagged = [
                s.id for s in self.staff_list
                if s.id in available_ids
                and s.tags and "带班领导" in s.tags and s.status == 1
            ]
            candidates = tagged if tagged else list(available_ids)

        # 过滤
        candidates = self.candidate_filter.apply(candidates, date_str, shift.id)

        # 打分排序
        scored = [
            (sid, self.scorer.score(sid, date_str, shift.id, is_night, is_weekend))
            for sid in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 选取
        available_count = len(scored)
        target = min(shift.leader_max, available_count)
        if target < shift.leader_min and available_count > 0:
            target = min(shift.leader_min, available_count)

        if available_count < shift.leader_min:
            conflicts.append(
                f"{date_str} {shift.name}：领导候选不足，最少需{shift.leader_min}人，仅{available_count}人可用"
            )

        return [sid for sid, _ in scored[:target]], conflicts

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

        # 不够从 rest 补充
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
    def _build_team_list(shift: SchShiftTemplate) -> list:
        teams = getattr(shift, "duty_teams", None) or []
        return sorted([t for t in teams if t.enabled], key=lambda t: t.priority)

    @staticmethod
    def _truncate_members(result: ScheduleResult, shift: SchShiftTemplate) -> list[int]:
        members = result.member_ids
        non_leader = [mid for mid in members if mid != result.leader_id]

        if len(non_leader) > shift.member_max:
            leader_part = [lid for lid in members if lid == result.leader_id]
            return leader_part + non_leader[: shift.member_max]

        max_total = shift.leader_max + shift.member_max
        if len(members) > max_total:
            leader_part = [lid for lid in members if lid == result.leader_id][: shift.leader_max]
            member_part = [mid for mid in members if mid != result.leader_id][: shift.member_max]
            return leader_part + member_part

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
            "night_shift_distribution": dict(night_dist),
            "conflicts_count": sum(len(r.conflicts) for r in results),
        }
