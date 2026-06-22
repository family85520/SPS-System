"""Pairing persistence and reconstruction for the scheduling engine."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pairing import SchPairing
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate
from app.models.staff import OrgStaff

logger = logging.getLogger("pairing_manager")


class PairingManager:
    """Manage stable slot/group pairings.

    Rules:
    - Persist pairings in ``sch_pairing`` after automatic generation.
    - If persisted pairings are absent, rebuild them from last month's
      schedules by reversing the scheduler's slot rotation.
    - Special/admin personnel are replacements, so they do not overwrite the
      regular pairing group when deriving history.
    """

    def __init__(self, db: AsyncSession, org_id: int):
        self.db = db
        self.org_id = org_id

    async def get_pairing(
        self,
        shift_id: int,
        slot_index: int,
        group_type: str,
    ) -> Optional[SchPairing]:
        result = await self.db.execute(
            select(SchPairing).where(
                SchPairing.org_id == self.org_id,
                SchPairing.shift_id == shift_id,
                SchPairing.slot_index == slot_index,
                SchPairing.group_type == group_type,
            )
        )
        return result.scalars().first()

    async def get_all_pairings(self, shift_id: int) -> list[SchPairing]:
        result = await self.db.execute(
            select(SchPairing).where(
                SchPairing.org_id == self.org_id,
                SchPairing.shift_id == shift_id,
            )
        )
        return list(result.scalars().all())

    async def set_pairing(
        self,
        shift_id: int,
        slot_index: int,
        group_type: str,
        staff_ids: list[int],
        is_new: list[bool],
    ) -> SchPairing:
        existing = await self.get_pairing(shift_id, slot_index, group_type)

        if existing:
            existing.staff_ids = staff_ids
            existing.is_new = is_new
            return existing

        pairing = SchPairing(
            org_id=self.org_id,
            shift_id=shift_id,
            slot_index=slot_index,
            group_type=group_type,
            staff_ids=staff_ids,
            is_new=is_new,
        )
        self.db.add(pairing)
        return pairing

    async def load_pairings(
        self,
        shift_id: int,
    ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
        all_pairings = await self.get_all_pairings(shift_id)
        result: dict[tuple[int, str], tuple[list[int], list[bool]]] = {}
        for pairing in all_pairings:
            result[(pairing.slot_index, pairing.group_type)] = (
                pairing.staff_ids or [],
                pairing.is_new or [False] * len(pairing.staff_ids or []),
            )
        return result

    async def save_pairings(
        self,
        shift_id: int,
        pairings: dict[tuple[int, str], tuple[list[int], list[bool]]],
    ) -> None:
        for (slot_index, group_type), (staff_ids, is_new) in pairings.items():
            await self.set_pairing(shift_id, slot_index, group_type, staff_ids, is_new)

    async def update_on_special_rotation(
        self,
        shift_id: int,
        departed_special: list[int],
        joined_special: list[int],
        departed_regular: list[int],
        joined_regular: list[int],
    ) -> None:
        all_pairings = await self.get_all_pairings(shift_id)

        joined_staff_map: dict[int, OrgStaff] = {}
        if joined_regular:
            joined_staff_list = list((await self.db.execute(
                select(OrgStaff).where(OrgStaff.id.in_(joined_regular))
            )).scalars().all())
            joined_staff_map = {staff.id: staff for staff in joined_staff_list}

        for pairing in all_pairings:
            staff_ids = pairing.staff_ids or []
            is_new = pairing.is_new or []
            new_staff_ids = list(staff_ids)
            new_is_new = list(is_new) or [False] * len(staff_ids)

            for index, staff_id in enumerate(staff_ids):
                if staff_id in departed_special:
                    replacement_index = sorted(departed_special).index(staff_id)
                    if replacement_index < len(joined_special):
                        new_staff_ids[index] = joined_special[replacement_index]
                        new_is_new[index] = False

            for index, staff_id in enumerate(staff_ids):
                if staff_id in departed_regular and staff_id not in departed_special:
                    replacement_index = sorted(departed_regular).index(staff_id)
                    if replacement_index < len(joined_regular):
                        replacement_id = joined_regular[replacement_index]
                        new_staff_ids[index] = replacement_id
                        joined_staff = joined_staff_map.get(replacement_id)
                        new_is_new[index] = self._is_new_employee(joined_staff)

            pairing.staff_ids = new_staff_ids
            pairing.is_new = new_is_new

    async def derive_from_schedule(
        self,
        shift_id: int,
        month_start: date,
        month_end: date,
        rotation_anchor_date: date | None = None,
    ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
        """Derive pairings from the latest historical schedule per slot/group.

        For a 3-slot day rotation:
        - ``slot_index = rotation_day % 3``
        - ``rotation_number = rotation_day // 3``
        - odd rotations swap the actual day/night group.

        Schedules are processed ascending by date, so later manual edits in the
        previous month overwrite earlier generated pairings for the same key.
        """
        shift = await self._load_shift(shift_id)
        target_type = "night" if self._is_night_shift(shift) else "day"
        special_ids = set(shift.special_pool or []) if (
            shift and getattr(shift, "special_enabled", False)
        ) else set()

        schedules = await self._load_schedules(shift_id, month_start, month_end)
        if not schedules:
            return {}

        schedule_ids = [schedule.id for schedule in schedules]
        details = await self._load_details(schedule_ids)
        if not details:
            return {}

        details_by_schedule: dict[int, list[SchScheduleDetail]] = {}
        schedule_id_set = set(schedule_ids)
        for detail in details:
            if detail.schedule_id in schedule_id_set:
                details_by_schedule.setdefault(detail.schedule_id, []).append(detail)

        result: dict[tuple[int, str], tuple[list[int], list[bool]]] = {}
        for schedule in sorted(schedules, key=lambda item: (item.date, item.id)):
            staff_ids = self._regular_staff_ids(
                details_by_schedule.get(schedule.id, []),
                special_ids,
            )
            if not staff_ids:
                continue

            slot_index, group_type = self._resolve_slot_and_group(
                schedule.date,
                target_type,
                rotation_anchor_date,
            )
            result[(slot_index, group_type)] = (
                staff_ids,
                [False] * len(staff_ids),
            )

        return result

    async def delete_pairings(self, shift_id: int) -> None:
        await self.db.execute(
            delete(SchPairing).where(
                SchPairing.org_id == self.org_id,
                SchPairing.shift_id == shift_id,
            )
        )

    async def _load_shift(self, shift_id: int) -> SchShiftTemplate | None:
        result = await self.db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id == shift_id)
        )
        return result.scalars().first()

    async def _load_schedules(
        self,
        shift_id: int,
        month_start: date,
        month_end: date,
    ) -> list[SchSchedule]:
        result = await self.db.execute(
            select(SchSchedule).where(
                SchSchedule.org_id == self.org_id,
                SchSchedule.shift_id == shift_id,
                SchSchedule.date >= month_start,
                SchSchedule.date <= month_end,
            )
        )
        return list(result.scalars().all())

    async def _load_details(self, schedule_ids: list[int]) -> list[SchScheduleDetail]:
        result = await self.db.execute(
            select(SchScheduleDetail).where(
                SchScheduleDetail.schedule_id.in_(schedule_ids)
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _regular_staff_ids(
        details: list[SchScheduleDetail],
        special_ids: set[int],
    ) -> list[int]:
        staff_ids: list[int] = []
        for detail in sorted(details, key=lambda item: item.id):
            if getattr(detail, "role_type", "member") == "leader":
                continue
            if detail.staff_id in special_ids:
                continue
            if detail.staff_id not in staff_ids:
                staff_ids.append(detail.staff_id)
        return staff_ids

    @staticmethod
    def _resolve_slot_and_group(
        schedule_date: date,
        target_type: str,
        rotation_anchor_date: date | None = None,
    ) -> tuple[int, str]:
        slot_count = 3
        anchor = rotation_anchor_date or date(schedule_date.year, schedule_date.month, 1)
        rotation_day = max(0, (schedule_date - anchor).days)
        slot_index = rotation_day % slot_count
        rotation_number = rotation_day // slot_count
        if rotation_number % 2 == 0:
            group_type = target_type
        else:
            group_type = "day" if target_type == "night" else "night"
        return slot_index, group_type

    @staticmethod
    def _is_night_shift(shift: SchShiftTemplate | None) -> bool:
        if not shift:
            return False

        is_night = getattr(shift, "is_night", None)
        if isinstance(is_night, bool):
            return is_night

        try:
            start_hour = int(str(shift.start_time).split(":")[0])
            end_hour = int(str(shift.end_time).split(":")[0])
            return start_hour >= 20 or end_hour <= 8
        except (AttributeError, TypeError, ValueError):
            return False

    @staticmethod
    def _is_new_employee(staff: OrgStaff | None) -> bool:
        if not staff or not getattr(staff, "tags", None):
            return False
        return any(tag in staff.tags for tag in ("新员工", "new", "new_employee"))
