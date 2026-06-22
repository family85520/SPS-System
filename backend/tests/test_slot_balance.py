from collections import Counter
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.engine.scheduler import AutoScheduler, IndividualStrategy


def make_staff(staff_id: int):
    staff = MagicMock()
    staff.id = staff_id
    staff.name = f"S{staff_id}"
    staff.status = 1
    staff.tags = []
    return staff


def make_shift(shift_id: int, start_time: str, end_time: str):
    shift = MagicMock()
    shift.id = shift_id
    shift.name = f"Shift_{shift_id}"
    shift.status = 1
    shift.leader_enabled = False
    shift.leader_min = 0
    shift.leader_max = 0
    shift.leader_count = 0
    shift.leader_pool = []
    shift.leader_rotation_frequency = "week"
    shift.leader_use_tag = False
    shift.leader_tag_name = "leader"
    shift.special_enabled = False
    shift.special_count = 0
    shift.special_pool = []
    shift.special_rotation_frequency = "month"
    shift.special_exclude_from_member = True
    shift.member_min = 2
    shift.member_max = 2
    shift.member_rotation_frequency = "day"
    shift.apply_days = [1, 2, 3, 4, 5, 6, 7]
    shift.constraint_ids = None
    shift.start_time = start_time
    shift.end_time = end_time
    shift.duration_hours = 8
    return shift


def test_12_staff_30_day_month_balances_five_day_and_five_night():
    day_shift = make_shift(1, "08:00", "16:00")
    night_shift = make_shift(2, "20:00", "08:00")
    scheduler = AutoScheduler(
        staff_list=[make_staff(staff_id) for staff_id in range(1, 13)],
        shift_templates=[day_shift, night_shift],
        constraints=[],
        special_rules=[],
        existing_schedules=[],
        existing_details=[],
    )
    strategy = IndividualStrategy(scheduler)
    candidates = list(range(1, 13))
    day_counts = Counter()
    night_counts = Counter()

    current = date(2026, 6, 1)
    for offset in range(30):
        date_str = (current + timedelta(days=offset)).isoformat()
        day_counts.update(
            strategy._slot_rotate_select(candidates, date_str, 2, day_shift)
        )
        night_counts.update(
            strategy._slot_rotate_select(candidates, date_str, 2, night_shift)
        )

    assert dict(day_counts) == {staff_id: 5 for staff_id in range(1, 13)}
    assert dict(night_counts) == {staff_id: 5 for staff_id in range(1, 13)}
