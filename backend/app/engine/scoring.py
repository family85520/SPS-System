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

    # 打分权重常量
    _WEIGHT_HOURS = 0.3
    _WEIGHT_NIGHT = 3.0
    _WEIGHT_WEEKEND = 2.0
    _PENALTY_SAME_DAY = 1000.0
    _PENALTY_CONSECUTIVE = 50.0
    _PENALTY_GAP_1_DAY = 25.0
    _PENALTY_GAP_2_DAY = 10.0
    _PENALTY_SAME_SHIFT_TYPE = 30.0  # 白夜交替：同类型班次惩罚

    def __init__(
        self,
        existing_schedules: list[SchSchedule],
        existing_details: list[SchScheduleDetail],
        shifts: dict[int, SchShiftTemplate],
    ):
        self.shifts = shifts

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

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def score(
        self,
        staff_id: int,
        target_date: str,
        shift_id: int,
        is_night_shift: bool = False,
        is_weekend: bool = False,
    ) -> float:
        """为候选人计算分数，分数越高越优先排班。"""
        s = 0.0

        # 1. 累计工时（工时越少 → 越优先）
        s -= self.staff_hours.get(staff_id, 0.0) * self._WEIGHT_HOURS

        # 2. 夜班均衡
        if is_night_shift:
            s -= self.staff_night_count.get(staff_id, 0) * self._WEIGHT_NIGHT

        # 3. 周末均衡
        if is_weekend:
            s -= self.staff_weekend_count.get(staff_id, 0) * self._WEIGHT_WEEKEND

        # 4. 当天已排班惩罚
        if target_date in self.staff_days.get(staff_id, set()):
            s -= self._PENALTY_SAME_DAY

        # 5. 连续排班惩罚
        s -= self._calc_proximity_penalty(staff_id, target_date)

        # 6. 白夜交替惩罚：相同班次类型降低优先级，促使白→夜→白交替
        target_type = "night" if is_night_shift else "day"
        if self.staff_last_shift_type.get(staff_id) == target_type:
            s -= self._PENALTY_SAME_SHIFT_TYPE

        return s

    def record_assignment(self, staff_id: int, target_date: str, shift_id: int) -> None:
        """记录一次排班分配（同一轮内连续打分时更新状态）。"""
        self.staff_days[staff_id].add(target_date)

        shift = self.shifts.get(shift_id)
        if shift:
            dur = self._calc_duration(shift.start_time, shift.end_time)
            self.staff_hours[staff_id] += dur

            if self._is_night(shift.start_time, shift.end_time):
                self.staff_night_count[staff_id] += 1

        if self._is_weekend(target_date):
            self.staff_weekend_count[staff_id] += 1

        # 记录本次班次类型，供下一轮白夜交替决策
        if shift:
            self.staff_last_shift_type[staff_id] = (
                "night" if self._is_night(shift.start_time, shift.end_time) else "day"
            )

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _bulk_load(self, details: list[SchScheduleDetail]) -> None:
        """从历史明细中批量初始化统计数据。"""
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

        # 推断每人最后一次排班的班次类型（用于白夜交替判断）
        staff_latest: dict[int, tuple] = {}  # staff_id -> (date, shift_id)
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
        """计算目标日期与最近排班日期的邻近惩罚。"""
        staff_dates = sorted(self.staff_days.get(staff_id, set()))
        if not staff_dates:
            return 0.0

        penalty = 0.0
        try:
            target_obj = date.fromisoformat(target_date)
        except ValueError:
            return 0.0

        for d_str in staff_dates[-5:]:  # 只看最近 5 天
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

    # ------------------------------------------------------------------ #
    #  纯工具方法（无状态）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_duration(start_time: str, end_time: str) -> float:
        """计算班次时长（小时），跨天自动 +24h。"""
        try:
            sh, sm = map(int, start_time.split(":"))
            eh, em = map(int, end_time.split(":"))
            dur = (eh * 60 + em - sh * 60 - sm) / 60
            return dur + 24 if dur <= 0 else dur
        except (ValueError, AttributeError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _is_night(start_time: str, end_time: str) -> bool:
        """判断是否夜班（20:00后开始 或 08:00前结束）。"""
        try:
            sh, _ = map(int, start_time.split(":"))
            eh, _ = map(int, end_time.split(":"))
            return sh >= 20 or eh <= 8
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _is_weekend(date_str: str) -> bool:
        """判断日期是否周末（周六=6, 周日=7）。"""
        try:
            return date.fromisoformat(date_str).isoweekday() >= 6
        except ValueError:
            return False
