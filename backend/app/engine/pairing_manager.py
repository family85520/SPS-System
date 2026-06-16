"""配对关系管理器 - 管理新老员工配对关系"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pairing import SchPairing
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.staff import OrgStaff

logger = logging.getLogger("pairing_manager")


class PairingManager:
    """配对关系管理器

    规则：
    1. 有上月历史数据取上月，没有则首次自动排班按规则随机生成
    2. 配对关系存储数据库，直到被特殊班次人员替换时才更新
    3. 所有排序统一使用 ID 排序
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
        """获取指定槽位的配对关系"""
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
        """获取指定班次的所有配对关系"""
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
        """保存或更新配对关系"""
        existing = await self.get_pairing(shift_id, slot_index, group_type)

        if existing:
            existing.staff_ids = staff_ids
            existing.is_new = is_new
            return existing
        else:
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
        """加载配对关系：优先从数据库读取，没有则返回空

        Returns:
            {(slot_index, group_type): (staff_ids, is_new)}
        """
        all_pairings = await self.get_all_pairings(shift_id)
        if all_pairings:
            result = {}
            for p in all_pairings:
                result[(p.slot_index, p.group_type)] = (p.staff_ids, p.is_new)
            return result
        return {}

    async def save_pairings(
        self,
        shift_id: int,
        pairings: dict[tuple[int, str], tuple[list[int], list[bool]]],
    ) -> None:
        """保存配对关系到数据库"""
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
        """特殊轮换时更新配对关系

        规则：
        1. special_pool 人员替换原位置
        2. 普通人员替换离开人员的原位置
        """
        all_pairings = await self.get_all_pairings(shift_id)

        for pairing in all_pairings:
            staff_ids = pairing.staff_ids or []
            is_new = pairing.is_new or []
            new_staff_ids = list(staff_ids)
            new_is_new = list(is_new)

            # 处理 special_pool 人员替换
            for i, sid in enumerate(staff_ids):
                if sid in departed_special:
                    # 找到对应的替换人员（按 ID 顺序）
                    idx = sorted(departed_special).index(sid)
                    if idx < len(joined_special):
                        new_staff_ids[i] = joined_special[idx]
                        new_is_new[i] = False  # 特殊人员不算新员工

            # 处理普通人员替换
            for i, sid in enumerate(staff_ids):
                if sid in departed_regular and sid not in departed_special:
                    # 找到对应的替换人员（按 ID 顺序）
                    idx = sorted(departed_regular).index(sid)
                    if idx < len(joined_regular):
                        new_staff_ids[i] = joined_regular[idx]
                        # 批量加载新员工信息判断身份
                        joined_staff_list = list((await self.db.execute(
                            select(OrgStaff).where(OrgStaff.id.in_(joined_regular))
                        )).scalars().all())
                        joined_staff_map = {s.id: s for s in joined_staff_list}
                        joined_staff = joined_staff_map.get(joined_regular[idx])
                        new_is_new[i] = (
                            joined_staff.tags and "新员工" in (joined_staff.tags or [])
                        ) if joined_staff else False

            pairing.staff_ids = new_staff_ids
            pairing.is_new = new_is_new

    async def derive_from_schedule(
        self,
        shift_id: int,
        month_start: date,
        month_end: date,
    ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
        """从上月排班记录推导配对关系

        通过分析连续多天的人员组合模式，找出稳定的槽位分组。

        Returns:
            {(slot_index, group_type): (staff_ids, is_new)}
        """
        # 1. 加载排班记录
        schedules = list((await self.db.execute(
            select(SchSchedule).where(
                SchSchedule.org_id == self.org_id,
                SchSchedule.shift_id == shift_id,
                SchSchedule.date >= month_start,
                SchSchedule.date <= month_end,
            )
        )).scalars().all())

        if not schedules:
            return {}

        schedule_ids = [s.id for s in schedules]
        details = list((await self.db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
        )).scalars().all())

        if not details:
            return {}

        # 2. 按日期分组人员
        day_staff: dict[str, list[int]] = defaultdict(list)
        schedule_map = {s.id: s for s in schedules}
        for d in details:
            s = schedule_map.get(d.schedule_id)
            if s:
                day_staff[str(s.date)].append(d.staff_id)

        if not day_staff:
            return {}

        # 3. 取前7天分析
        sorted_dates = sorted(day_staff.keys())[:7]
        if not sorted_dates:
            return {}

        # 4. 统计每对人一起出现的频率
        pair_cooccurrence: Counter = Counter()
        for date_str in sorted_dates:
            staff_on_day = day_staff[date_str]
            for i in range(len(staff_on_day)):
                for j in range(i + 1, len(staff_on_day)):
                    pair = tuple(sorted([staff_on_day[i], staff_on_day[j]]))
                    pair_cooccurrence[pair] += 1

        # 5. 提取高频配对
        threshold = max(3, len(sorted_dates) // 2)
        stable_pairs = [(pair, count) for pair, count in pair_cooccurrence.items() if count >= threshold]
        stable_pairs.sort(key=lambda x: -x[1])

        if not stable_pairs:
            # 降级：取第一天数据简单分组
            return await self._fallback_derive(day_staff, sorted_dates[0])

        # 6. 将配对分配到3个槽位
        result = {}
        pair_idx = 0
        for slot_idx in range(3):
            if pair_idx + 1 >= len(stable_pairs):
                break
            day_pair = stable_pairs[pair_idx][0]
            night_pair = stable_pairs[pair_idx + 1][0]
            result[(slot_idx, "day")] = (list(day_pair), [False] * len(day_pair))
            result[(slot_idx, "night")] = (list(night_pair), [False] * len(night_pair))
            pair_idx += 2

        return result

    async def _fallback_derive(
        self,
        day_staff: dict[str, list[int]],
        first_date: str,
    ) -> dict[tuple[int, str], tuple[list[int], list[bool]]]:
        """降级方案：取第一天数据简单分组"""
        staff = day_staff.get(first_date, [])
        if not staff:
            return {}

        # 批量加载人员信息判断新老
        staff_list = list((await self.db.execute(
            select(OrgStaff).where(OrgStaff.id.in_(staff))
        )).scalars().all())
        staff_map = {s.id: s for s in staff_list}

        def _is_new(staff_id: int) -> bool:
            s = staff_map.get(staff_id)
            return bool(s and s.tags and "新员工" in (s.tags or []))

        # 简单分组：前一半 day，后一半 night
        mid = len(staff) // 2
        day_group = staff[:mid]
        night_group = staff[mid:]

        result = {}
        per_slot = max(1, len(day_group) // 3)
        for slot_idx in range(3):
            start = slot_idx * per_slot
            end = start + per_slot
            if start < len(day_group):
                result[(slot_idx, "day")] = (
                    day_group[start:end],
                    [_is_new(sid) for sid in day_group[start:end]]
                )
            if start < len(night_group):
                result[(slot_idx, "night")] = (
                    night_group[start:end],
                    [_is_new(sid) for sid in night_group[start:end]]
                )

        return result

    async def delete_pairings(self, shift_id: int) -> None:
        """删除指定班次的所有配对关系"""
        await self.db.execute(
            delete(SchPairing).where(
                SchPairing.org_id == self.org_id,
                SchPairing.shift_id == shift_id,
            )
        )
