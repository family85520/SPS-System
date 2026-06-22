"""约束校验引擎 - 核心校验逻辑"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from app.engine.models import CheckResult, RuleCheck, Violation
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate


class ConstraintChecker:
    """约束校验器"""

    def __init__(
        self,
        schedules: list[SchSchedule],
        details: list[SchScheduleDetail],
        constraints: list,
        special_rules: list,
        shifts: dict[int, SchShiftTemplate],
        staff_map: dict[int, str],
    ):
        self.schedules = schedules
        self.details = details
        self.constraints = constraints
        self.special_rules = special_rules
        self.shifts = shifts
        self.staff_map = staff_map

        self._build_indexes()

    def _build_indexes(self):
        self.schedule_map: dict[int, SchSchedule] = {s.id: s for s in self.schedules}

        self.staff_details: dict[int, list[SchScheduleDetail]] = defaultdict(list)
        self.date_details: dict[str, list[SchScheduleDetail]] = defaultdict(list)
        self.date_shift_details: dict[tuple, list[SchScheduleDetail]] = defaultdict(list)
        self.schedule_details: dict[int, list[SchScheduleDetail]] = defaultdict(list)

        for d in self.details:
            schedule = self.schedule_map.get(d.schedule_id)
            if not schedule:
                continue
            date_str = str(schedule.date)
            self.staff_details[d.staff_id].append(d)
            self.date_details[date_str].append(d)
            self.date_shift_details[(date_str, schedule.shift_id)].append(d)
            self.schedule_details[d.schedule_id].append(d)

        self.staff_schedule_dates: dict[int, list[tuple[str, int]]] = defaultdict(list)
        for d in self.details:
            schedule = self.schedule_map.get(d.schedule_id)
            if schedule:
                self.staff_schedule_dates[d.staff_id].append((str(schedule.date), schedule.shift_id))

        self.staff_special_rules: dict[int, list] = defaultdict(list)
        for r in self.special_rules:
            self.staff_special_rules[r.staff_id].append(r)

    def check_all(self, scope_org_id: Optional[int] = None) -> CheckResult:
        result = CheckResult()

        applicable = [c for c in self.constraints if c.enabled]
        if scope_org_id:
            applicable = [
                c for c in applicable
                if not hasattr(c, 'scope_type') or c.scope_type != "org"
                or scope_org_id in (c.scope_ids or [])
            ]
        applicable.sort(key=lambda x: getattr(x, 'priority', 999))

        for constraint in applicable:
            rule_type = constraint.rule_type
            params = constraint.params or {}
            rule_name = constraint.rule_name or rule_type

            checker = getattr(self, f'_check_{rule_type.lower()}', None)
            if checker:
                try:
                    violations = checker(constraint.id, rule_name, params)
                except Exception:
                    violations = []

                if violations:
                    for v in violations:
                        if v.severity == "error":
                            result.failed.append(v)
                        else:
                            result.warnings.append(v)
                else:
                    result.passed.append(RuleCheck(
                        rule_type=rule_type, rule_name=rule_name,
                        passed=True, message="校验通过",
                    ))
            else:
                result.passed.append(RuleCheck(
                    rule_type=rule_type, rule_name=rule_name,
                    passed=True, message="暂未实现该规则校验",
                ))

        self._check_special_rules(result)
        return result

    def check_single(
        self, schedule_id: int, staff_id: int, schedule_date: str, shift_id: int,
    ) -> list[Violation]:
        violations = []
        constraints = [c for c in self.constraints if c.enabled]

        for constraint in constraints:
            checker = getattr(self, f'_check_{constraint.rule_type.lower()}_single', None)
            if checker:
                violations.extend(checker(
                    schedule_id, staff_id, schedule_date, shift_id,
                    constraint.rule_name or constraint.rule_type, constraint.params or {},
                ))

        violations.extend(self._check_special_rules_single(staff_id, schedule_id, schedule_date, shift_id))
        return violations

    # ==================== 辅助方法 ====================

    def _get_staff_name(self, staff_id: int) -> str:
        return self.staff_map.get(staff_id, f"ID:{staff_id}")

    def _find_violation_schedule_id(self, staff_id: int, date_str: str) -> int | None:
        for d in self.staff_details[staff_id]:
            s = self.schedule_map.get(d.schedule_id)
            if s and str(s.date) == date_str:
                return d.schedule_id
        return None

    def _calc_shift_duration(self, shift: SchShiftTemplate) -> float:
        try:
            sh, sm = map(int, shift.start_time.split(":"))
            eh, em = map(int, shift.end_time.split(":"))
            dur = (eh * 60 + em - sh * 60 - sm) / 60
            return dur + 24 if dur <= 0 else dur
        except (ValueError, AttributeError):
            return 0.0

    def _is_night_shift(self, shift: SchShiftTemplate) -> bool:
        try:
            sh, _ = map(int, shift.start_time.split(":"))
            eh, _ = map(int, shift.end_time.split(":"))
            return sh >= 20 or eh <= 8
        except (ValueError, AttributeError):
            return False

    # ==================== 约束规则校验（全局） ====================

    def _check_max_continuous_days(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        max_days = params.get("max_days", 5)
        violations = []

        for staff_id, dates in self.staff_schedule_dates.items():
            sorted_dates = sorted(set(d[0] for d in dates))
            if len(sorted_dates) < 2:
                continue

            consecutive = 1
            for i in range(1, len(sorted_dates)):
                prev = date.fromisoformat(sorted_dates[i - 1])
                curr = date.fromisoformat(sorted_dates[i])
                if (curr - prev).days == 1:
                    consecutive += 1
                    if consecutive > max_days:
                        sched_id = self._find_violation_schedule_id(staff_id, sorted_dates[i])
                        if sched_id:
                            violations.append(Violation(
                                rule_type="MAX_CONTINUOUS_DAYS", rule_name=rule_name,
                                message=f"{self._get_staff_name(staff_id)} 已连续工作 {consecutive} 天，超过上限 {max_days} 天",
                                schedule_id=sched_id, staff_id=staff_id,
                                date=sorted_dates[i], severity="warning",
                            ))
                            break
                else:
                    consecutive = 1

        return violations

    def _check_min_rest_after_continuous(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        rest_days = params.get("rest_days", 1)
        violations = []

        for staff_id, dates in self.staff_schedule_dates.items():
            sorted_dates = sorted(set(d[0] for d in dates))
            if len(sorted_dates) < 2:
                continue

            consecutive = 1
            for i in range(1, len(sorted_dates)):
                prev = date.fromisoformat(sorted_dates[i - 1])
                curr = date.fromisoformat(sorted_dates[i])
                if (curr - prev).days == 1:
                    consecutive += 1
                else:
                    if consecutive >= 2:
                        gap = (curr - prev).days
                        if gap < rest_days + 1:
                            sched_id = self._find_violation_schedule_id(staff_id, sorted_dates[i])
                            if sched_id:
                                violations.append(Violation(
                                    rule_type="MIN_REST_AFTER_CONTINUOUS", rule_name=rule_name,
                                    message=f"{self._get_staff_name(staff_id)} 连续工作 {consecutive} 天后仅休息 {gap - 1} 天，不足 {rest_days} 天",
                                    schedule_id=sched_id, staff_id=staff_id,
                                    date=sorted_dates[i], severity="warning",
                                ))
                                break
                    consecutive = 1

        return violations

    def _check_min_shift_interval(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        min_hours = params.get("hours", 8)
        violations = []

        for staff_id, dates in self.staff_schedule_dates.items():
            sorted_entries = sorted(dates, key=lambda x: (x[0], x[1]))
            if len(sorted_entries) < 2:
                continue

            for i in range(1, len(sorted_entries)):
                prev_date, prev_shift_id = sorted_entries[i - 1]
                curr_date, curr_shift_id = sorted_entries[i]

                if prev_date != curr_date:
                    continue

                prev_shift = self.shifts.get(prev_shift_id)
                curr_shift = self.shifts.get(curr_shift_id)
                if not prev_shift or not curr_shift:
                    continue

                try:
                    peh, pem = map(int, prev_shift.end_time.split(":"))
                    csh, csm = map(int, curr_shift.start_time.split(":"))
                    gap_hours = ((csh * 60 + csm) - (peh * 60 + pem)) / 60

                    if gap_hours < min_hours:
                        sched_id = self._find_violation_schedule_id(staff_id, curr_date)
                        if sched_id:
                            violations.append(Violation(
                                rule_type="MIN_SHIFT_INTERVAL", rule_name=rule_name,
                                message=f"{self._get_staff_name(staff_id)} 在 {curr_date} 的班次间隔仅 {gap_hours:.1f} 小时，不足 {min_hours} 小时",
                                schedule_id=sched_id, staff_id=staff_id,
                                date=curr_date, severity="error",
                            ))
                            break
                except (ValueError, AttributeError):
                    continue

        return violations

    def _check_min_rest_after_night(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        min_hours = params.get("hours", 12)
        violations = []

        for staff_id, dates in self.staff_schedule_dates.items():
            sorted_entries = sorted(dates, key=lambda x: (x[0], x[1]))
            if len(sorted_entries) < 2:
                continue

            for i in range(1, len(sorted_entries)):
                prev_date, prev_shift_id = sorted_entries[i - 1]
                curr_date, curr_shift_id = sorted_entries[i]

                prev_shift = self.shifts.get(prev_shift_id)
                curr_shift = self.shifts.get(curr_shift_id)
                if not prev_shift or not curr_shift:
                    continue

                try:
                    psh, _ = map(int, prev_shift.start_time.split(":"))
                    peh, _ = map(int, prev_shift.end_time.split(":"))
                    csh, _ = map(int, curr_shift.start_time.split(":"))

                    is_night = psh >= 20 or peh <= 8
                    if not is_night:
                        continue

                    prev_date_obj = date.fromisoformat(prev_date)
                    curr_date_obj = date.fromisoformat(curr_date)
                    day_diff = (curr_date_obj - prev_date_obj).days

                    if peh <= csh:
                        gap = (day_diff * 24 * 60 + csh * 60 - peh * 60) / 60
                    else:
                        gap = ((day_diff + 1) * 24 * 60 - peh * 60 + csh * 60) / 60

                    if gap < min_hours:
                        sched_id = self._find_violation_schedule_id(staff_id, curr_date)
                        if sched_id:
                            violations.append(Violation(
                                rule_type="MIN_REST_AFTER_NIGHT", rule_name=rule_name,
                                message=f"{self._get_staff_name(staff_id)} 夜班后仅休息 {gap:.1f} 小时，不足 {min_hours} 小时",
                                schedule_id=sched_id, staff_id=staff_id,
                                date=curr_date, severity="error",
                            ))
                            break
                except (ValueError, AttributeError):
                    continue

        return violations

    def _check_max_shifts_per_day(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        max_count = params.get("count", 1)
        violations = []

        for date_str, details in self.date_details.items():
            staff_count: dict[int, int] = defaultdict(int)
            for d in details:
                staff_count[d.staff_id] += 1

            for staff_id, count in staff_count.items():
                if count > max_count:
                    for d in details:
                        if d.staff_id == staff_id:
                            violations.append(Violation(
                                rule_type="MAX_SHIFTS_PER_DAY", rule_name=rule_name,
                                message=f"{self._get_staff_name(staff_id)} 在 {date_str} 排了 {count} 个班次，超过上限 {max_count}",
                                schedule_id=d.schedule_id, staff_id=staff_id,
                                date=date_str, severity="error",
                            ))
                            break

        return violations

    def _check_max_weekly_hours(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        max_hours = params.get("hours", 48)
        violations = []

        staff_weekly_hours: dict[tuple[int, int], float] = defaultdict(float)
        staff_weekly_details: dict[tuple[int, int], list] = defaultdict(list)

        for d in self.details:
            schedule = self.schedule_map.get(d.schedule_id)
            if not schedule:
                continue
            shift = self.shifts.get(schedule.shift_id)
            if not shift:
                continue

            week_num = schedule.date.isocalendar()[1]
            key = (d.staff_id, week_num)
            dur = self._calc_shift_duration(shift)
            if dur > 0:
                staff_weekly_hours[key] += dur
                staff_weekly_details[key].append(d)

        for (staff_id, week_num), hours in staff_weekly_hours.items():
            if hours > max_hours:
                details = staff_weekly_details[(staff_id, week_num)]
                if details:
                    d = details[0]
                    s = self.schedule_map.get(d.schedule_id)
                    violations.append(Violation(
                        rule_type="MAX_WEEKLY_HOURS", rule_name=rule_name,
                        message=f"{self._get_staff_name(staff_id)} 第{week_num}周累计工作 {hours:.1f} 小时，超过上限 {max_hours} 小时",
                        schedule_id=d.schedule_id, staff_id=staff_id,
                        date=str(s.date) if s else "未知", severity="warning",
                    ))

        return violations

    # ==================== 特殊规则校验 ====================

    def _check_special_rules(self, result: CheckResult):
        for d in self.details:
            schedule = self.schedule_map.get(d.schedule_id)
            if not schedule:
                continue

            violations = self._check_special_rules_single(
                d.staff_id, d.schedule_id, str(schedule.date), schedule.shift_id
            )
            for v in violations:
                if v.severity == "error":
                    result.failed.append(v)
                else:
                    result.warnings.append(v)

    def _check_special_rules_single(
        self, staff_id: int, schedule_id: int, schedule_date: str, shift_id: int,
    ) -> list[Violation]:
        violations = []
        rules = self.staff_special_rules.get(staff_id, [])

        for rule in rules:
            if rule.effective_from and schedule_date < str(rule.effective_from):
                continue
            if rule.effective_to and schedule_date > str(rule.effective_to):
                continue

            params = rule.params or {}
            staff_name = self._get_staff_name(staff_id)
            shift = self.shifts.get(shift_id)
            shift_name = shift.name if shift else f"ID:{shift_id}"

            if rule.rule_type == "exclude_shift":
                if shift_id in params.get("exclude_shift_ids", []):
                    violations.append(Violation(
                        rule_type="SPECIAL_EXCLUDE_SHIFT", rule_name="特殊规则-不排某班次",
                        message=f"{staff_name} 的特殊规则不允许排「{shift_name}」",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))

            elif rule.rule_type == "include_shift":
                included = params.get("include_shift_ids", [])
                if included and shift_id not in included:
                    violations.append(Violation(
                        rule_type="SPECIAL_INCLUDE_SHIFT", rule_name="特殊规则-仅排某班次",
                        message=f"{staff_name} 的特殊规则仅允许排指定班次，不包含「{shift_name}」",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))

            elif rule.rule_type == "exclude_date":
                if schedule_date in params.get("exclude_dates", []):
                    violations.append(Violation(
                        rule_type="SPECIAL_EXCLUDE_DATE", rule_name="特殊规则-特定日期不排班",
                        message=f"{staff_name} 的特殊规则不允许在 {schedule_date} 排班",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))

            elif rule.rule_type == "exclude_weekday":
                d_obj = date.fromisoformat(schedule_date)
                weekday = d_obj.isoweekday()
                if weekday in params.get("exclude_weekdays", []) and shift_id in params.get("exclude_shift_ids", []):
                    weekday_names = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
                    violations.append(Violation(
                        rule_type="SPECIAL_EXCLUDE_WEEKDAY", rule_name="特殊规则-特定星期不排某班",
                        message=f"{staff_name} 的特殊规则不允许在{weekday_names.get(weekday, '')}排「{shift_name}」",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))

        return violations

    # ==================== 单条校验方法（实时调用） ====================

    def _check_max_continuous_days_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        max_days = params.get("max_days", 5)
        dates = sorted(set(d[0] for d in self.staff_schedule_dates.get(staff_id, [])))
        if schedule_date not in dates:
            dates.append(schedule_date)
            dates.sort()

        if schedule_date not in dates:
            return []

        consecutive = 1
        idx = dates.index(schedule_date)
        i = idx - 1
        while i >= 0:
            if (date.fromisoformat(dates[i + 1]) - date.fromisoformat(dates[i])).days == 1:
                consecutive += 1
                i -= 1
            else:
                break
        i = idx + 1
        while i < len(dates):
            if (date.fromisoformat(dates[i]) - date.fromisoformat(dates[i - 1])).days == 1:
                consecutive += 1
                i += 1
            else:
                break

        if consecutive > max_days:
            return [Violation(
                rule_type="MAX_CONTINUOUS_DAYS", rule_name=rule_name,
                message=f"{self._get_staff_name(staff_id)} 将连续工作 {consecutive} 天，超过上限 {max_days} 天",
                schedule_id=schedule_id, staff_id=staff_id,
                date=schedule_date, severity="warning",
            )]
        return []

    def _check_max_shifts_per_day_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        max_count = params.get("count", 1)
        current_count = sum(
            1 for d in self.date_details.get(schedule_date, [])
            if d.staff_id == staff_id
        ) + 1

        if current_count > max_count:
            return [Violation(
                rule_type="MAX_SHIFTS_PER_DAY", rule_name=rule_name,
                message=f"{self._get_staff_name(staff_id)} 在 {schedule_date} 已排 {current_count} 个班次，超过上限 {max_count}",
                schedule_id=schedule_id, staff_id=staff_id,
                date=schedule_date, severity="error",
            )]
        return []

    def _check_max_weekly_hours_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        max_hours = params.get("hours", 48)
        d_obj = date.fromisoformat(schedule_date)
        week_num = d_obj.isocalendar()[1]

        current_hours = 0.0
        for d_date, d_shift_id in self.staff_schedule_dates.get(staff_id, []):
            d_date_obj = date.fromisoformat(d_date)
            if d_date_obj.isocalendar()[1] == week_num:
                shift = self.shifts.get(d_shift_id)
                if shift:
                    current_hours += self._calc_shift_duration(shift)

        current_shift = self.shifts.get(shift_id)
        if current_shift:
            current_hours += self._calc_shift_duration(current_shift)

        if current_hours > max_hours:
            return [Violation(
                rule_type="MAX_WEEKLY_HOURS", rule_name=rule_name,
                message=f"{self._get_staff_name(staff_id)} 第{week_num}周累计工作将达 {current_hours:.1f} 小时，超过上限 {max_hours} 小时",
                schedule_id=schedule_id, staff_id=staff_id,
                date=schedule_date, severity="warning",
            )]
        return []

    def _check_min_shift_interval_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        min_hours = params.get("hours", 8)
        curr_shift = self.shifts.get(shift_id)
        if not curr_shift:
            return []

        violations = []
        for d_date, d_shift_id in self.staff_schedule_dates.get(staff_id, []):
            if d_date != schedule_date:
                continue
            prev_shift = self.shifts.get(d_shift_id)
            if not prev_shift:
                continue
            try:
                peh, pem = map(int, prev_shift.end_time.split(":"))
                csh, csm = map(int, curr_shift.start_time.split(":"))
                gap = ((csh * 60 + csm) - (peh * 60 + pem)) / 60
                if 0 < gap < min_hours:
                    violations.append(Violation(
                        rule_type="MIN_SHIFT_INTERVAL", rule_name=rule_name,
                        message=f"{self._get_staff_name(staff_id)} 在 {schedule_date} 的班次间隔仅 {gap:.1f} 小时，不足 {min_hours} 小时",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))
            except (ValueError, AttributeError):
                continue

        return violations

    def _check_min_rest_after_night_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        min_hours = params.get("hours", 12)
        curr_shift = self.shifts.get(shift_id)
        if not curr_shift:
            return []

        violations = []
        for d_date, d_shift_id in self.staff_schedule_dates.get(staff_id, []):
            prev_shift = self.shifts.get(d_shift_id)
            if not prev_shift:
                continue
            try:
                psh, _ = map(int, prev_shift.start_time.split(":"))
                peh, _ = map(int, prev_shift.end_time.split(":"))
                is_night = psh >= 20 or peh <= 8
                if not is_night:
                    continue

                csh, _ = map(int, curr_shift.start_time.split(":"))
                prev_date_obj = date.fromisoformat(d_date)
                curr_date_obj = date.fromisoformat(schedule_date)
                day_diff = (curr_date_obj - prev_date_obj).days

                if peh <= csh:
                    gap = (day_diff * 24 * 60 + csh * 60 - peh * 60) / 60
                else:
                    gap = ((day_diff + 1) * 24 * 60 - peh * 60 + csh * 60) / 60

                if 0 < gap < min_hours:
                    violations.append(Violation(
                        rule_type="MIN_REST_AFTER_NIGHT", rule_name=rule_name,
                        message=f"{self._get_staff_name(staff_id)} 夜班后仅休息 {gap:.1f} 小时，不足 {min_hours} 小时",
                        schedule_id=schedule_id, staff_id=staff_id,
                        date=schedule_date, severity="error",
                    ))
            except (ValueError, AttributeError):
                continue

        return violations

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

    def _check_holiday_mode_single(
        self, schedule_id: int, staff_id: int, schedule_date: str,
        shift_id: int, rule_name: str, params: dict,
    ) -> list[Violation]:
        # 单条校验时，节假日模式需在全局校验中判断
        return []

    def _check_weekend_diff(self, rule_id: int, rule_name: str, params: dict) -> list[Violation]:
        """周末差异化排班"""
        mode = params.get("mode", "reduced")
        violations = []

        if mode == "reduced":
            reduced_count = params.get("reduced_count", 1)
            weekday_count = params.get("weekday_count", 0)
            if weekday_count <= 0:
                return []

            for date_str, details in self.date_details.items():
                try:
                    d_obj = date.fromisoformat(date_str)
                except ValueError:
                    continue
                if d_obj.isoweekday() < 6:
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
