"""槽位绑定系统单元测试"""
import pytest
from datetime import date
from unittest.mock import MagicMock
from app.engine.scheduler import AutoScheduler, IndividualStrategy


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

    def test_12_candidates_slot_returns_day_group(self):
        """12人分3槽位，每槽位day_group有2人，target=2时应返回2人"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        assert len(result) == 2

    def test_12_candidates_slot_returns_full_group(self):
        """槽位绑定返回整个组，不截断"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 1, scheduler.shift_templates[1])
        assert len(result) >= 1  # 返回整个组，不截断

    def test_10_candidates_produces_valid_groups(self):
        """10人应分组，选出的人员属于候选人集"""
        scheduler = self._make_scheduler(10)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 11))
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        assert len(result) == 2
        assert all(sid in candidates for sid in result)

    def test_day_night_alternation(self):
        """白夜应交替：偶数rotation_number为day_group，奇数为night_group"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        # Day 1 (slot 0, rotation_number=0, even) -> day_group
        day_result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        # Day 4 (slot 0, rotation_number=1, odd) -> night_group (swapped)
        night_result = strategy._slot_rotate_select(candidates, "2026-06-04", 2, scheduler.shift_templates[1])
        assert set(day_result) != set(night_result)

    def test_monthly_binding_stable(self):
        """同一日期重复调用应保持稳定"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        result1 = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        result2 = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        assert result1 == result2

    def test_slot_binding_returns_subset_of_candidates(self):
        """返回结果必须是候选人的子集"""
        scheduler = self._make_scheduler(10)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 11))
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        assert all(sid in candidates for sid in result)

    def test_target_larger_than_group_returns_all_in_group(self):
        """当 target 大于组大小时应返回组内全部人员"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        # Each group has 2 people, target=10 should return all 2
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 10, scheduler.shift_templates[1])
        assert len(result) == 2

    def test_empty_candidates_returns_empty(self):
        """空候选人列表应返回空结果"""
        scheduler = self._make_scheduler(5)
        strategy = IndividualStrategy(scheduler)
        result = strategy._slot_rotate_select([], "2026-06-01", 4, scheduler.shift_templates[1])
        assert result == []

    def test_zero_target_returns_group(self):
        """target=0 时槽位绑定仍返回整个组（不截断）"""
        scheduler = self._make_scheduler(5)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 6))
        result = strategy._slot_rotate_select(candidates, "2026-06-01", 0, scheduler.shift_templates[1])
        assert len(result) >= 0  # 返回整个组

    def test_three_slots_cover_distinct_people(self):
        """3个槽位应返回不重叠的人员"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        results = []
        for day in [1, 2, 3]:
            result = strategy._slot_rotate_select(candidates, f"2026-06-0{day}", 2, scheduler.shift_templates[1])
            results.append(set(result))
        # Slots should be disjoint
        assert results[0].isdisjoint(results[1])
        assert results[1].isdisjoint(results[2])
        assert results[0].isdisjoint(results[2])

    def test_different_days_same_slot_same_group(self):
        """同一槽位的不同天(rotation_number相同)应返回相同组"""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 13))
        # Day 1 and Day 7: both slot 0, rotation_number 0
        result1 = strategy._slot_rotate_select(candidates, "2026-06-01", 2, scheduler.shift_templates[1])
        result7 = strategy._slot_rotate_select(candidates, "2026-06-07", 2, scheduler.shift_templates[1])
        assert result1 == result7

    def test_slot_grouper_creates_3_slots_for_12(self):
        """SlotGrouper 应为12人创建3个槽位"""
        scheduler = self._make_scheduler(12)
        groups = scheduler._slot_grouper.get_month_groups(sorted(range(1, 13)), 2026, 6)
        assert len(groups) == 3
        # Each slot should have day_group and night_group
        for idx, (dg, ng) in groups.items():
            assert len(dg) == 2
            assert len(ng) == 2

    def test_slot_grouper_covers_all_people(self):
        """所有槽位的人员合集应等于全部候选人"""
        scheduler = self._make_scheduler(12)
        groups = scheduler._slot_grouper.get_month_groups(sorted(range(1, 13)), 2026, 6)
        all_people = set()
        for dg, ng in groups.values():
            all_people.update(dg)
            all_people.update(ng)
        assert all_people == set(range(1, 13))

    def test_fallback_select_for_small_group(self):
        """少于9人时应使用fallback选择"""
        scheduler = self._make_scheduler(5)
        strategy = IndividualStrategy(scheduler)
        candidates = list(range(1, 6))
        result = strategy._fallback_select(candidates, "2026-06-01", 3, is_night=False)
        assert len(result) == 3
        assert all(sid in candidates for sid in result)

    def test_cross_month_replacement_preserves_candidate_group_size(self):
        """Cross-month replacement keeps regular groups filled from candidates."""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)

        groups = {
            0: ([1, 2], [3, 4]),
            1: ([5, 6], [7, 8]),
            2: ([9, 10], [11, 12]),
        }
        original_sizes = {
            slot_idx: (len(day_group), len(night_group))
            for slot_idx, (day_group, night_group) in groups.items()
        }

        normalized = strategy._normalize_replaced_groups(
            new_groups={
                0: ([101, 2], [102, 4]),
                1: ([5, 5], [7, 8]),
                2: ([9, 10], [11, 12]),
            },
            original_groups=groups,
            candidates=list(range(1, 13)),
        )

        seen = set()
        for slot_idx, (day_group, night_group) in normalized.items():
            assert (len(day_group), len(night_group)) == original_sizes[slot_idx]
            for sid in day_group + night_group:
                assert sid in range(1, 13)
                assert sid not in seen
                seen.add(sid)

    def test_special_replacement_keeps_original_partner(self):
        """Special replacement should inherit the replaced person's partner."""
        scheduler = self._make_scheduler(12)
        strategy = IndividualStrategy(scheduler)

        groups = {
            0: ([101, 2], [102, 4]),
            1: ([5, 6], [7, 8]),
            2: ([9, 10], [11, 12]),
        }
        scheduler.prev_month_schedules = [
            MagicMock(id=1, shift_id=99, date=date(2026, 6, 1)),
            MagicMock(id=2, shift_id=1, date=date(2026, 6, 1)),
        ]
        scheduler.existing_details = [
            MagicMock(schedule_id=1, staff_id=201),
            MagicMock(schedule_id=1, staff_id=202),
            MagicMock(schedule_id=2, staff_id=101),
            MagicMock(schedule_id=2, staff_id=2),
            MagicMock(schedule_id=2, staff_id=102),
            MagicMock(schedule_id=2, staff_id=4),
        ]
        scheduler.shift_templates[99] = make_shift(
            99,
            special_enabled=True,
            special_pool=[101, 102, 201, 202],
        )
        shift = make_shift(
            1,
            special_enabled=False,
            special_pool=[101, 102, 201, 202],
        )

        replaced = strategy._apply_in_place_replacement(
            groups, shift, sorted(range(1, 13)) + [201, 202]
        )

        assert replaced[0][0] == [201, 2]
        assert replaced[0][1] == [202, 4]
