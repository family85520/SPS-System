"""公平性打分模块 - 为候选人员计算优先级分数"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate


class FairnessScorer:
    """公平性打分器

    职责：
    1. 统计每位人员的历史排班数据（工时、夜班、周末等）
    2. 为候选人计算优先级分数（分数越高越优先）
    3. 动态记录本轮新增排班，保证同一轮内打分状态实时更新
    """

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

        self.staff_days: dict[int, set[str]] = defaultdict(set)
        self.staff_hours: dict[int, float] = defaultdict(float)
        self.staff_night_count: dict[int, int] = defaultdict(int)
        self.staff_weekend_count: dict[int, int] = defaultdict(int)

        self.staff_last_shift_type: dict[int, str] = {}

        self._schedule_index: dict[int, SchSchedule] = {
            s.id: s for s in existing_schedules
        }

        self._bulk_load(existing_details)

    def score(
        self,
        staff_id: int,
        target_date: str,
        shift_id: int,
        is_night_shift: bool = False,
        is_weekend: bool = False,
    ) -> float:
        s = 0.0

        s -= self.staff_hours.get(staff_id, 0.0) * self._WEIGHT_HOURS

        if is_night_shift:
            s -= self.staff_night_count.get(staff_id, 0) * self._WEIGHT_NIGHT

        if is_weekend:
            s -= self.staff_weekend_count.get(staff_id, 0) * self._WEIGHT_WEEKEND

        if target_date in self.staff_days.get(staff_id, set()):
            s -= self._PENALTY_SAME_DAY

        s -= self._calc_proximity_penalty(staff_id, target_date)

        target_type = "night" if is_night_shift else "day"
        if self.staff_last_shift_type.get(staff_id) == target_type:
            s -= self._PENALTY_SAME_SHIFT_TYPE

        return s

    def record_assignment(self, staff_id: int, target_date: str, shift_id: int) -> None:
        self.staff_days[staff_id].add(target_date)

        shift = self.shifts.get(shift_id)
        if shift:
            dur = self._calc_duration(shift.start_time, shift.end_time)
            self.staff_hours[staff_id] += dur

            if self._is_night(shift.start_time, shift.end_time):
                self.staff_night_count[staff_id] += 1

        if self._is_weekend(target_date):
            self.staff_weekend_count[staff_id] += 1

        if shift:
            self.staff_last_shift_type[staff_id] = (
                "night" if self._is_night(shift.start_time, shift.end_time) else "day"
            )

    def _bulk_load(self, details: list[SchScheduleDetail]) -> None:
        for d in details:
            schedule = self._schedule_index.get(d.schedule_id)
            if not schedule:
                continue

            date_str = str(schedule.date)
            self.staff_days[d.staff_id].add(date_str)

            shift = self.shifts.get(schedule.shift_id)
            if shift:
                dur = self._calc_duration(shift.start_time, shift.end_time)
                self.staff_hours[d.staff_id] += dur

                if self._is_night(shift.start_time, shift.end_time):
                    self.staff_night_count[d.staff_id] += 1

            if self._is_weekend(date_str):
                self.staff_weekend_count[d.staff_id] += 1

        staff_latest: dict[int, tuple] = {}
        for d in details:
            schedule = self._schedule_index.get(d.schedule_id)
            if not schedule:
                continue
            existing = staff_latest.get(d.staff_id)
            if not existing or schedule.date > existing[0]:
                staff_latest[d.staff_id] = (schedule.date, schedule.shift_id)
        for staff_id, (_, shift_id) in staff_latest.items():
            shift = self.shifts.get(shift_id)
            if shift:
                self.staff_last_shift_type[staff_id] = (
                    "night" if self._is_night(shift.start_time, shift.end_time) else "day"
                )

    def _calc_proximity_penalty(self, staff_id: int, target_date: str) -> float:
        staff_dates = sorted(self.staff_days.get(staff_id, set()))
        if not staff_dates:
            return 0.0

        try:
            target_obj = date.fromisoformat(target_date)
        except ValueError:
            return 0.0

        penalty = 0.0
        for d_str in staff_dates[-5:]:
            try:
                d_obj = date.fromisoformat(d_str)
            except ValueError:
                continue
            gap = abs((target_obj - d_obj).days)
            if gap == 1:
                penalty += self._PENALTY_CONSECUTIVE
            elif gap == 2:
                penalty += self._PENALTY_GAP_1_DAY
            elif gap == 3:
                penalty += self._PENALTY_GAP_2_DAY

        return penalty

    @staticmethod
    def _calc_duration(start_time: str, end_time: str) -> float:
        try:
            sh, sm = map(int, start_time.split(":"))
            eh, em = map(int, end_time.split(":"))
            dur = (eh * 60 + em - sh * 60 - sm) / 60
            return dur + 24 if dur <= 0 else dur
        except (ValueError, AttributeError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _is_night(start_time: str, end_time: str) -> bool:
        try:
            sh, _ = map(int, start_time.split(":"))
            eh, _ = map(int, end_time.split(":"))
            return sh >= 20 or eh <= 8
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _is_weekend(date_str: str) -> bool:
        try:
            return date.fromisoformat(date_str).isoweekday() >= 6
        except ValueError:
            return False
