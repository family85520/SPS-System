from datetime import date
from unittest.mock import MagicMock

from app.engine.scheduler import AutoScheduler, IndividualStrategy


def make_staff(staff_id: int):
    staff = MagicMock()
    staff.id = staff_id
    staff.name = f"S{staff_id}"
    staff.status = 1
    staff.tags = []
    return staff


def make_shift(shift_id: int, *, special_enabled: bool = False):
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
    shift.special_enabled = special_enabled
    shift.special_count = 3 if special_enabled else 0
    shift.special_pool = []
    shift.special_rotation_frequency = "month"
    shift.special_exclude_from_member = True
    shift.member_min = 2
    shift.member_max = 2
    shift.member_rotation_frequency = "day"
    shift.apply_days = [1, 2, 3, 4, 5, 6, 7]
    shift.constraint_ids = None
    shift.start_time = "08:00"
    shift.end_time = "16:00"
    shift.duration_hours = 8
    return shift


def make_scheduler():
    day_shift = make_shift(1)
    admin_shift = make_shift(99, special_enabled=True)
    return AutoScheduler(
        staff_list=[make_staff(staff_id) for staff_id in range(1, 16)],
        shift_templates=[day_shift, admin_shift],
        constraints=[],
        special_rules=[],
        existing_schedules=[],
        existing_details=[],
    )


def test_slot_rotation_continues_across_31_day_month():
    scheduler = make_scheduler()
    scheduler._slot_rotation_anchor_date = date(2026, 6, 1)
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    candidates = list(range(1, 13))

    june_1 = strategy._slot_rotate_select(candidates, "2026-06-01", 2, shift)
    june_2 = strategy._slot_rotate_select(candidates, "2026-06-02", 2, shift)
    august_1 = strategy._slot_rotate_select(candidates, "2026-08-01", 2, shift)

    assert august_1 == june_2
    assert august_1 != june_1


def test_admin_rotation_replaces_by_historical_position_order():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    groups = {
        0: ([1, 2], [3, 4]),
        1: ([5, 6], [7, 8]),
        2: ([9, 10], [11, 12]),
    }
    current_candidates = [1, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]

    admin_schedule = MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1))
    day_schedule = MagicMock(id=101, shift_id=shift.id, date=date(2026, 6, 1))
    scheduler.prev_month_schedules = [admin_schedule, day_schedule]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=201, staff_id=14),
        MagicMock(schedule_id=201, staff_id=15),
        MagicMock(schedule_id=101, staff_id=1),
    ]
    scheduler._prev_special_members[admin_shift.id] = [11, 2, 3]

    replaced = strategy._apply_in_place_replacement(
        groups,
        shift,
        current_candidates,
    )

    assert replaced[0] == ([1, 14], [15, 4])
    assert replaced[1] == ([5, 6], [7, 8])
    assert replaced[2] == ([9, 10], [13, 12])


def test_replacement_members_survive_candidate_filtering():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    scheduler._loaded_pairings[shift.id] = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([3, 4], [False, False]),
        (1, "day"): ([5, 6], [False, False]),
        (1, "night"): ([7, 8], [False, False]),
        (2, "day"): ([9, 10], [False, False]),
        (2, "night"): ([11, 12], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=202, shift_id=admin_shift.id, date=date(2026, 6, 2)),
        MagicMock(id=203, shift_id=admin_shift.id, date=date(2026, 6, 3)),
        MagicMock(id=101, shift_id=shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=202, staff_id=14),
        MagicMock(schedule_id=203, staff_id=15),
        MagicMock(schedule_id=101, staff_id=1),
    ]
    scheduler._prev_special_members[admin_shift.id] = [11, 2, 3]

    filtered_candidates = [1, 4, 5, 6, 7, 8, 9, 10, 12]
    result = strategy._slot_rotate_select(
        filtered_candidates,
        "2026-06-01",
        2,
        shift,
    )

    assert result == [1, 14]


def test_replacement_members_are_not_reused_across_day_and_night_templates():
    scheduler = make_scheduler()
    night_shift = make_shift(2)
    night_shift.start_time = "20:00"
    night_shift.end_time = "08:00"
    scheduler.shift_templates[night_shift.id] = night_shift
    strategy = IndividualStrategy(scheduler)
    day_shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    pairings = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([3, 4], [False, False]),
    }
    scheduler._loaded_pairings[day_shift.id] = pairings
    scheduler._loaded_pairings[night_shift.id] = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([5, 3], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=202, shift_id=admin_shift.id, date=date(2026, 6, 2)),
        MagicMock(id=203, shift_id=admin_shift.id, date=date(2026, 6, 3)),
        MagicMock(id=101, shift_id=day_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=102, shift_id=night_shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=202, staff_id=14),
        MagicMock(schedule_id=203, staff_id=15),
        MagicMock(schedule_id=101, staff_id=1),
        MagicMock(schedule_id=102, staff_id=5),
    ]
    scheduler._prev_special_members[admin_shift.id] = [2, 3, 4]

    candidates = [1, 13, 14, 15]
    day_result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, day_shift)
    night_result = strategy._slot_rotate_select(candidates, "2026-06-01", 2, night_shift)

    assert day_result == [1, 13]
    assert night_result == [14, 15]


def test_bound_partner_is_restored_when_candidate_pool_has_only_one_member():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    scheduler._loaded_pairings[shift.id] = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([3, 4], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=101, shift_id=shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=101, staff_id=1),
    ]
    scheduler._prev_special_members[admin_shift.id] = [2]

    result = strategy._slot_rotate_select([1], "2026-06-01", 1, shift)

    assert result == [1, 13]


def test_current_admin_member_is_excluded_from_regular_shift():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]

    scheduler._current_special_locked.add(2)
    members, conflicts = strategy._assign_members(
        shift,
        "2026-07-01",
        [1, 2, 3],
        [],
        max_slots=2,
    )

    assert 2 not in members
    assert not conflicts


def test_admin_returnees_are_mapped_by_admin_position_not_first_come_first_served():
    scheduler = make_scheduler()
    night_shift = make_shift(2)
    night_shift.start_time = "20:00"
    night_shift.end_time = "08:00"
    scheduler.shift_templates[night_shift.id] = night_shift
    strategy = IndividualStrategy(scheduler)
    day_shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    # 13/14/15 represent last month's admin returnees, e.g. Feng/Shao/Cai.
    # 2/3/4 represent people entering admin this month. Position mapping means:
    # 2 -> 13, 3 -> 14, 4 -> 15.
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=202, shift_id=admin_shift.id, date=date(2026, 6, 2)),
        MagicMock(id=203, shift_id=admin_shift.id, date=date(2026, 6, 3)),
        MagicMock(id=101, shift_id=day_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=102, shift_id=night_shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=202, staff_id=14),
        MagicMock(schedule_id=203, staff_id=15),
        MagicMock(schedule_id=101, staff_id=1),
        MagicMock(schedule_id=102, staff_id=5),
    ]
    scheduler._prev_special_members[admin_shift.id] = [2, 3, 4]
    scheduler._loaded_pairings[day_shift.id] = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([6, 7], [False, False]),
    }
    scheduler._loaded_pairings[night_shift.id] = {
        (0, "day"): ([8, 9], [False, False]),
        (0, "night"): ([5, 3], [False, False]),
    }

    day_result = strategy._slot_rotate_select([1, 13, 14, 15], "2026-06-01", 2, day_shift)
    night_result = strategy._slot_rotate_select([5, 13, 14, 15], "2026-06-01", 2, night_shift)

    assert day_result == [1, 13]
    assert night_result == [5, 14]
    assert 15 not in day_result


def test_current_full_admin_roster_maps_regular_admin_entrants():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    groups = {
        0: ([1, 2], [3, 4]),
        1: ([5, 6], [7, 8]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=101, shift_id=shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=13),
        MagicMock(schedule_id=201, staff_id=14),
        MagicMock(schedule_id=201, staff_id=15),
        MagicMock(schedule_id=101, staff_id=1),
    ]
    scheduler._prev_special_members[admin_shift.id] = [2]
    scheduler._current_admin_members[admin_shift.id] = [2, 5, 7]
    scheduler._monthly_locked.update({5, 7})

    replaced = strategy._apply_in_place_replacement(
        groups,
        shift,
        [1, 3, 4, 6, 8],
    )

    assert replaced[1] == ([14, 6], [15, 8])


def test_month_start_regular_shift_replaces_new_special_before_admin_day():
    scheduler = make_scheduler()
    night_shift = make_shift(2)
    night_shift.start_time = "20:00"
    night_shift.end_time = "08:00"
    scheduler.shift_templates[night_shift.id] = night_shift
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.special_pool = [8]
    admin_shift.special_count = 1
    scheduler._loaded_pairings[night_shift.id] = {
        (0, "day"): ([1, 2], [False, False]),
        (0, "night"): ([8, 14], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 7, 1)),
        MagicMock(id=101, shift_id=night_shift.id, date=date(2026, 7, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=32),
        MagicMock(schedule_id=201, staff_id=5),
        MagicMock(schedule_id=101, staff_id=8),
        MagicMock(schedule_id=101, staff_id=14),
    ]

    scheduler._prepare_monthly_special_locks(strategy, [night_shift, admin_shift])
    result = strategy._slot_rotate_select(
        [1, 2, 14, 32],
        "2026-08-01",
        2,
        night_shift,
    )

    assert result == [32, 14]
    assert 8 not in result


def test_month_start_locks_admin_regular_members_before_weekend_admin_shift():
    scheduler = make_scheduler()
    night_shift = make_shift(2)
    night_shift.start_time = "20:00"
    night_shift.end_time = "08:00"
    scheduler.shift_templates[night_shift.id] = night_shift
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.apply_days = [1, 2, 3, 4, 5]
    admin_shift.special_pool = [8, 32]
    admin_shift.special_count = 1
    admin_shift.member_max = 2
    admin_shift.member_rotation_frequency = "month"
    scheduler._loaded_pairings[night_shift.id] = {
        (0, "day"): ([5, 14], [False, False]),
        (0, "night"): ([8, 16], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 7, 1)),
        MagicMock(id=101, shift_id=night_shift.id, date=date(2026, 7, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=32),
        MagicMock(schedule_id=201, staff_id=11),
        MagicMock(schedule_id=101, staff_id=5),
        MagicMock(schedule_id=101, staff_id=14),
    ]

    scheduler._prepare_monthly_special_locks(
        strategy,
        [night_shift, admin_shift],
        [5, 11, 14, 16, 32],
        "2026-08-01",
    )

    assert scheduler._current_admin_members[admin_shift.id] == [8, 5]
    assert 5 in scheduler._monthly_locked


def test_cross_month_replacement_does_not_rebind_other_slots_later():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    scheduler._loaded_pairings[shift.id] = {
        (0, "day"): ([8, 14], [False, False]),
        (0, "night"): ([1, 2], [False, False]),
        (1, "day"): ([7, 16], [False, False]),
        (1, "night"): ([3, 4], [False, False]),
        (2, "day"): ([5, 6], [False, False]),
        (2, "night"): ([9, 10], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=101, shift_id=shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=32),
        MagicMock(schedule_id=201, staff_id=11),
        MagicMock(schedule_id=101, staff_id=8),
        MagicMock(schedule_id=101, staff_id=14),
    ]
    scheduler._prev_special_members[admin_shift.id] = [8]
    scheduler._current_special_locked.add(8)

    first_result = strategy._slot_rotate_select(
        [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 14, 16, 32],
        "2026-07-01",
        2,
        shift,
    )
    second_result = strategy._slot_rotate_select(
        [1, 2, 3, 4, 5, 6, 9, 10, 11, 14, 16, 32],
        "2026-07-02",
        2,
        shift,
    )

    assert first_result == [32, 14]
    assert second_result == [16]
    assert scheduler._new_pairings[shift.id][(0, "day")][0] == [32, 14]
    assert scheduler._new_pairings[shift.id][(1, "day")][0] == [7, 16]
    assert 11 not in scheduler._new_pairings[shift.id][(1, "day")][0]


def test_monthly_admin_lock_survives_day_shift_month_boundary_replacement():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    scheduler._slot_grouper._current_month = 2026 * 12 + 8
    scheduler._monthly_locked.add(5)
    scheduler._loaded_pairings[shift.id] = {
        (0, "day"): ([5, 14], [False, False]),
        (0, "night"): ([1, 2], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 8, 1)),
        MagicMock(id=101, shift_id=shift.id, date=date(2026, 8, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=32),
        MagicMock(schedule_id=101, staff_id=5),
        MagicMock(schedule_id=101, staff_id=14),
    ]

    result = strategy._slot_rotate_select(
        [14, 32],
        "2026-09-01",
        2,
        shift,
    )

    assert result == [32, 14]
    assert 5 in scheduler._monthly_locked


def test_new_regular_admin_members_are_taken_from_different_shift_templates():
    scheduler = make_scheduler()
    night_shift = make_shift(2)
    night_shift.start_time = "20:00"
    night_shift.end_time = "08:00"
    scheduler.shift_templates[night_shift.id] = night_shift
    strategy = IndividualStrategy(scheduler)
    day_shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    admin_shift.special_pool = [2, 3, 4, 5, 6, 7]
    admin_shift.special_count = 3
    scheduler.prev_month_schedules = [
        MagicMock(id=101, shift_id=day_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=102, shift_id=day_shift.id, date=date(2026, 6, 2)),
        MagicMock(id=201, shift_id=night_shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=101, staff_id=2),
        MagicMock(schedule_id=102, staff_id=3),
        MagicMock(schedule_id=201, staff_id=4),
    ]

    selected = strategy._derive_special_from_other_shifts(admin_shift, admin_shift.special_pool)

    assert selected == [2, 4]


def test_new_admin_members_are_taken_from_different_bound_groups():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    day_shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    admin_shift.special_pool = [2, 3, 4, 5, 6, 7]
    admin_shift.special_count = 3
    scheduler._loaded_pairings[day_shift.id] = {
        (0, "day"): ([2, 3], [False, False]),
        (0, "night"): ([4, 5], [False, False]),
        (1, "day"): ([6, 7], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=101, shift_id=day_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=102, shift_id=day_shift.id, date=date(2026, 6, 2)),
        MagicMock(id=103, shift_id=day_shift.id, date=date(2026, 6, 3)),
        MagicMock(id=104, shift_id=day_shift.id, date=date(2026, 6, 4)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=101, staff_id=2),
        MagicMock(schedule_id=102, staff_id=2),
        MagicMock(schedule_id=103, staff_id=3),
        MagicMock(schedule_id=104, staff_id=4),
        MagicMock(schedule_id=104, staff_id=6),
    ]

    selected = strategy._derive_special_from_other_shifts(admin_shift, admin_shift.special_pool)

    assert selected == [2, 4, 6]
    assert 3 not in selected


def test_admin_fill_does_not_add_second_member_from_same_bound_group():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    day_shift = scheduler.shift_templates[1]
    admin_shift = scheduler.shift_templates[99]

    admin_shift.special_pool = [2, 3, 4, 5, 6, 7]
    admin_shift.special_count = 3
    scheduler._loaded_pairings[day_shift.id] = {
        (0, "day"): ([2, 3], [False, False]),
        (0, "night"): ([4, 5], [False, False]),
        (1, "day"): ([6, 7], [False, False]),
    }
    scheduler.prev_month_schedules = [
        MagicMock(id=101, shift_id=day_shift.id, date=date(2026, 6, 1)),
        MagicMock(id=102, shift_id=day_shift.id, date=date(2026, 6, 2)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=101, staff_id=2),
        MagicMock(schedule_id=102, staff_id=3),
    ]

    selected, conflicts = strategy._assign_special_group(
        admin_shift,
        "2026-07-01",
        [],
    )

    assert selected == [2, 4, 6]
    assert 3 not in selected
    assert not conflicts


def test_admin_regular_members_skip_source_group_used_by_special_member_old_group_case():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.member_rotation_frequency = "month"
    admin_shift.special_pool = [2]
    scheduler._special_source_shift_by_member = {
        2: (1, 0, "day"),
        3: (1, 0, "day"),
        4: (1, 0, "night"),
        6: (1, 1, "day"),
    }
    scheduler._prev_special_members[admin_shift.id] = [2]

    selected = strategy._slot_rotate_select(
        [3, 4, 6, 8, 9],
        "2026-07-01",
        2,
        admin_shift,
    )

    assert selected == [4, 6]
    assert 3 not in selected


def test_admin_regular_members_skip_source_group_used_by_special_member():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.member_rotation_frequency = "month"
    admin_shift.special_pool = [2]
    scheduler._special_source_shift_by_member = {
        2: (1, 0, "day"),
        3: (1, 1, "night"),
        4: (2, 0, "day"),
        6: (3, 0, "day"),
        8: None,
    }
    scheduler._prev_special_members[admin_shift.id] = [2]

    selected = strategy._slot_rotate_select(
        [3, 4, 6, 8],
        "2026-08-01",
        2,
        admin_shift,
    )

    assert set(selected) == {3, 4}
    assert 8 not in selected


def test_admin_regular_members_exclude_previous_admin_returnees():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.member_rotation_frequency = "month"
    admin_shift.special_pool = [2]
    scheduler.prev_month_schedules = [
        MagicMock(id=201, shift_id=admin_shift.id, date=date(2026, 6, 1)),
    ]
    scheduler.existing_details = [
        MagicMock(schedule_id=201, staff_id=4),
        MagicMock(schedule_id=201, staff_id=5),
    ]

    selected, conflicts = strategy._assign_members(
        admin_shift,
        "2026-07-01",
        [3, 6, 7, 8, 9],
        [2],
        max_slots=2,
    )

    assert len(selected) == 2
    assert 4 not in selected
    assert 5 not in selected
    assert not conflicts


def test_admin_regular_members_rotate_beyond_special_pool_across_months():
    scheduler = make_scheduler()
    strategy = IndividualStrategy(scheduler)
    admin_shift = scheduler.shift_templates[99]

    admin_shift.member_rotation_frequency = "month"
    admin_shift.special_pool = [8, 32]
    admin_shift.special_count = 1

    july_selected = strategy._slot_rotate_select(
        [5, 7, 9, 11, 14, 16],
        "2026-07-01",
        2,
        admin_shift,
    )
    scheduler._monthly_member_cache.clear()
    august_selected = strategy._slot_rotate_select(
        [5, 7, 9, 11, 14, 16],
        "2026-08-01",
        2,
        admin_shift,
    )

    assert july_selected != august_selected
    assert set(july_selected).isdisjoint(admin_shift.special_pool)
    assert set(august_selected).isdisjoint(admin_shift.special_pool)
