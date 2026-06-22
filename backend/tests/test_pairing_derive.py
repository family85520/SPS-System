from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engine.pairing_manager import PairingManager


class TestPairingDeriveFromSchedule:
    @pytest.mark.asyncio
    async def test_reverses_slot_rotation(self):
        db = AsyncMock()
        shift = MagicMock()
        shift.is_night = False
        shift.special_enabled = False
        shift.special_pool = []

        schedule_1 = MagicMock(id=101, date=date(2026, 6, 1))
        schedule_4 = MagicMock(id=104, date=date(2026, 6, 4))

        details = [
            MagicMock(id=1, schedule_id=101, staff_id=1, role_type="member"),
            MagicMock(id=2, schedule_id=101, staff_id=2, role_type="member"),
            MagicMock(id=3, schedule_id=104, staff_id=3, role_type="member"),
            MagicMock(id=4, schedule_id=104, staff_id=4, role_type="member"),
        ]

        shift_result = MagicMock()
        shift_result.scalars.return_value.first.return_value = shift
        schedule_result = MagicMock()
        schedule_result.scalars.return_value.all.return_value = [schedule_1, schedule_4]
        detail_result = MagicMock()
        detail_result.scalars.return_value.all.return_value = details
        db.execute.side_effect = [shift_result, schedule_result, detail_result]

        mgr = PairingManager(db, org_id=4)
        result = await mgr.derive_from_schedule(
            shift_id=1,
            month_start=date(2026, 6, 1),
            month_end=date(2026, 6, 30),
        )

        assert result[(0, "day")] == ([1, 2], [False, False])
        assert result[(0, "night")] == ([3, 4], [False, False])

    @pytest.mark.asyncio
    async def test_latest_history_overrides_same_slot_group(self):
        db = AsyncMock()
        shift = MagicMock()
        shift.is_night = False
        shift.special_enabled = True
        shift.special_pool = [99]

        schedule_1 = MagicMock(id=101, date=date(2026, 6, 1))
        schedule_7 = MagicMock(id=107, date=date(2026, 6, 7))

        details = [
            MagicMock(id=1, schedule_id=101, staff_id=10, role_type="member"),
            MagicMock(id=2, schedule_id=101, staff_id=11, role_type="member"),
            MagicMock(id=3, schedule_id=107, staff_id=99, role_type="member"),
            MagicMock(id=4, schedule_id=107, staff_id=20, role_type="member"),
            MagicMock(id=5, schedule_id=107, staff_id=21, role_type="member"),
            MagicMock(id=6, schedule_id=107, staff_id=30, role_type="leader"),
        ]

        shift_result = MagicMock()
        shift_result.scalars.return_value.first.return_value = shift
        schedule_result = MagicMock()
        schedule_result.scalars.return_value.all.return_value = [schedule_7, schedule_1]
        detail_result = MagicMock()
        detail_result.scalars.return_value.all.return_value = details
        db.execute.side_effect = [shift_result, schedule_result, detail_result]

        mgr = PairingManager(db, org_id=4)
        result = await mgr.derive_from_schedule(
            shift_id=1,
            month_start=date(2026, 6, 1),
            month_end=date(2026, 6, 30),
        )

        assert result[(0, "day")] == ([20, 21], [False, False])

    @pytest.mark.asyncio
    async def test_derives_slot_with_continuous_rotation_anchor(self):
        db = AsyncMock()
        shift = MagicMock()
        shift.is_night = False
        shift.special_enabled = False
        shift.special_pool = []

        schedule = MagicMock(id=201, date=date(2026, 8, 1))
        details = [
            MagicMock(id=1, schedule_id=201, staff_id=5, role_type="member"),
            MagicMock(id=2, schedule_id=201, staff_id=14, role_type="member"),
        ]

        shift_result = MagicMock()
        shift_result.scalars.return_value.first.return_value = shift
        schedule_result = MagicMock()
        schedule_result.scalars.return_value.all.return_value = [schedule]
        detail_result = MagicMock()
        detail_result.scalars.return_value.all.return_value = details
        db.execute.side_effect = [shift_result, schedule_result, detail_result]

        mgr = PairingManager(db, org_id=4)
        result = await mgr.derive_from_schedule(
            shift_id=1,
            month_start=date(2026, 8, 1),
            month_end=date(2026, 8, 31),
            rotation_anchor_date=date(2026, 6, 1),
        )

        assert result[(1, "day")] == ([5, 14], [False, False])
        assert (0, "day") not in result
