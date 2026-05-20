"""首页看板服务（全异步）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SysUser, OrgOrganization, OrgStaff, SchConstraint, SysMessage, SysAnnouncement
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate
from app.utils.time_helper import to_local_short as _to_local_short


class DashboardService:

    @staticmethod
    async def get_overview(db: AsyncSession, *, user_id: int, org_id: Optional[int] = None) -> dict:
        """获取首页看板全部数据"""

        # ── 组织数量 ──
        org_count = (await db.execute(
            select(func.count(OrgOrganization.id)).where(OrgOrganization.status == 1)
        )).scalar() or 0

        # ── 人员总数 ──
        staff_count = (await db.execute(
            select(func.count(OrgStaff.id)).where(OrgStaff.status == 1)
        )).scalar() or 0

        # ── 启用规则数 ──
        active_rules_count = (await db.execute(
            select(func.count(SchConstraint.id)).where(SchConstraint.enabled == True)
        )).scalar() or 0

        # ── 待处理调班 ──
        pending_swap_count = 0
        try:
            from app.models.swap import SchSwapRequest
            pending_swap_count = (await db.execute(
                select(func.count(SchSwapRequest.id)).where(
                    SchSwapRequest.status.in_(["pending_confirm", "pending_claim", "pending_approve"])
                )
            )).scalar() or 0
        except (ImportError, Exception):
            pass

        # ── 今日值班 ──
        today_duty = await _get_today_duty(db, date.today(), org_id)

        # ── 未读消息 ──
        unread_messages = (await db.execute(
            select(func.count(SysMessage.id)).where(
                SysMessage.receiver_id == user_id,
                SysMessage.is_read == False,
                SysMessage.deleted_at.is_(None),
                SysMessage.title.notilike("[已删除]%"),
            )
        )).scalar() or 0

        # ── 最近公告（最多5条） ──
        recent_anns = (await db.execute(
            select(SysAnnouncement)
            .where(SysAnnouncement.is_active == True)
            .order_by(SysAnnouncement.created_at.desc())
            .limit(5)
        )).scalars().all()
        recent_notices = [
            {
                "id": a.id,
                "title": a.title,
                "created_at": _to_local_short(a.created_at),
            }
            for a in recent_anns
        ]

        # ── 约束冲突数（暂无持久化冲突表，设为 0） ──
        constraint_warnings = 0

        # ── 排班状态 ──
        schedule_status = await _get_schedule_status(db, org_id)

        return {
            "org_count": org_count,
            "staff_count": staff_count,
            "active_rules_count": active_rules_count,
            "pending_swap_count": pending_swap_count,
            "today_duty": today_duty,
            "unread_messages": unread_messages,
            "recent_notices": recent_notices,
            "constraint_warnings": constraint_warnings,
            "schedule_status": schedule_status,
        }


# ========== 私有辅助函数 ==========

async def _get_today_duty(db: AsyncSession, today: date, org_id: Optional[int]) -> list:
    """获取今日值班安排"""
    query = select(SchSchedule).where(SchSchedule.date == today)
    if org_id:
        query = query.where(SchSchedule.org_id == org_id)

    schedules = list((await db.execute(query)).scalars().all())
    if not schedules:
        return []

    # 班次模板
    shift_ids = list({s.shift_id for s in schedules})
    shifts: dict = {}
    if shift_ids:
        rows = (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_ids))
        )).scalars().all()
        shifts = {s.id: s for s in rows}

    # 排班明细
    schedule_ids = [s.id for s in schedules]
    details = list((await db.execute(
        select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
    )).scalars().all())

    detail_map: dict[int, list] = {}
    all_staff_ids: set[int] = set()
    for d in details:
        detail_map.setdefault(d.schedule_id, []).append(d)
        all_staff_ids.add(d.staff_id)

    leader_ids = [s.leader_staff_id for s in schedules if s.leader_staff_id]
    all_staff_ids.update(leader_ids)

    # 人员姓名
    staff_map: dict[int, str] = {}
    if all_staff_ids:
        rows = (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(list(all_staff_ids)))
        )).all()
        staff_map = {row[0]: row[1] for row in rows}

    duty_list = []
    for s in schedules:
        shift = shifts.get(s.shift_id)
        shift_name = shift.name if shift else "未知班次"
        leader_name = staff_map.get(s.leader_staff_id, "") if s.leader_staff_id else ""

        members = []
        for d in detail_map.get(s.id, []):
            if d.role_type == "leader" and leader_name:
                continue
            members.append(staff_map.get(d.staff_id, "未知"))

        duty_list.append({
            "shift_name": shift_name,
            "leader": leader_name,
            "members": members,
        })

    return duty_list


async def _get_schedule_status(db: AsyncSession, org_id: Optional[int]) -> str:
    """获取当月排班状态"""
    today = date.today()
    first_day = date(today.year, today.month, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)

    query = select(SchSchedule).where(
        SchSchedule.date >= first_day, SchSchedule.date < next_month,
    )
    if org_id:
        query = query.where(SchSchedule.org_id == org_id)

    schedules = list((await db.execute(query)).scalars().all())
    if not schedules:
        return "empty"

    statuses = {s.status for s in schedules}
    if statuses == {1}:
        return "published"
    if 1 in statuses:
        return "partial_published"
    return "draft"
