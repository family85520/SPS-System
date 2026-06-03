"""排班管理服务"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from collections import defaultdict
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrgOrganization, OrgStaff
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.swap import SchSwapRequest
from app.models.shift_template import SchShiftTemplate
from app.services.message_service import MessageService
from app.utils.time_helper import to_local_str as _to_local_str


# 排班状态常量
STATUS_DRAFT = 0
STATUS_PUBLISHED = 1
STATUS_RECALLED = 2
STATUS_PENDING_APPROVAL = 3


class ScheduleService:
    """排班管理服务"""

    # ==================== 列表查询 ====================

    @staticmethod
    async def get_list(
        db: AsyncSession,
        *,
        org_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        shift_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """获取排班列表"""
        query = select(SchSchedule)
        query = _apply_schedule_filters(query, org_id, start_date, end_date, status, shift_id)

        # 按人员ID筛选：通过排班明细表关联查找该人员参与的排班
        if staff_id is not None:
            detail_subq = (
                select(SchScheduleDetail.schedule_id)
                .where(SchScheduleDetail.staff_id == staff_id)
                .distinct()
            )
            query = query.where(SchSchedule.id.in_(detail_subq))

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

        query = query.order_by(SchSchedule.date.desc(), SchSchedule.id)
        query = query.offset((page - 1) * page_size).limit(page_size)

        schedules = (await db.execute(query)).scalars().all()

        # 批量查询关联数据
        shift_map = await _get_shift_map(db, {s.shift_id for s in schedules})
        org_map = await _get_org_map(db, {s.org_id for s in schedules})
        leader_ids = [s.leader_staff_id for s in schedules if s.leader_staff_id]
        leader_map = await _get_staff_map(db, leader_ids)
        detail_map, staff_map = await _get_detail_map(db, [s.id for s in schedules])

        items = [
            _serialize_schedule_list_item(s, shift_map, org_map, leader_map, detail_map, staff_map)
            for s in schedules
        ]
        return {"items": items, "total": total}

    # ==================== 日历查询 ====================

    @staticmethod
    async def get_calendar(
        db: AsyncSession,
        *,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
        status: Optional[int] = None,
    ) -> dict:
        """获取排班日历数据"""
        query = select(SchSchedule).where(
            SchSchedule.date >= start_date, SchSchedule.date <= end_date,
        )
        if org_id is not None:
            query = query.where(SchSchedule.org_id == org_id)
        if status is not None:
            query = query.where(SchSchedule.status == status)
        query = query.order_by(SchSchedule.date, SchSchedule.id)

        schedules = list((await db.execute(query)).scalars().unique().all())
        if not schedules:
            return {"dates": []}

        shift_map = await _get_shift_map(db, {s.shift_id for s in schedules})
        leader_ids = [s.leader_staff_id for s in schedules if s.leader_staff_id]
        leader_map = await _get_staff_map(db, leader_ids)
        detail_map, staff_map = await _get_detail_map(db, [s.id for s in schedules])

        # 按日期分组
        date_dict: dict[str, dict] = {}
        for s in schedules:
            date_str = str(s.date)
            if date_str not in date_dict:
                date_dict[date_str] = {"date": date_str, "shifts": []}

            shift = shift_map.get(s.shift_id)
            leaders = []
            members = []
            for d in detail_map.get(s.id, []):
                if d.role_type == "leader":
                    leaders.append({
                        "staff_id": d.staff_id,
                        "name": staff_map.get(d.staff_id, "未知"),
                        "role_type": "leader",
                    })
                else:
                    members.append({
                        "staff_id": d.staff_id,
                        "name": staff_map.get(d.staff_id, "未知"),
                        "role_type": d.role_type,
                        "is_substitute": d.is_substitute,
                        "note": d.note,
                    })

            date_dict[date_str]["shifts"].append({
                "schedule_id": s.id,
                "shift_template_id": s.shift_id,
                "shift_name": getattr(shift, "name", "未知班次"),
                "shift_color": getattr(shift, "color", "#999999"),
                "start_time": getattr(shift, "start_time", ""),
                "end_time": getattr(shift, "end_time", ""),
                "leader": leaders[0] if leaders else None,
                "leaders": leaders,
                "members": members,
                "status": s.status,
                "source": s.source,
            })

        return {"dates": [date_dict[d] for d in sorted(date_dict.keys())]}

    # ==================== 单条查询 ====================

    @staticmethod
    async def get_by_id(db: AsyncSession, schedule_id: int) -> dict:
        """获取排班记录详情"""
        schedule = (await db.execute(
            select(SchSchedule).where(SchSchedule.id == schedule_id)
        )).scalars().first()
        if not schedule:
            raise ValueError(f"排班记录不存在（id={schedule_id}）")

        # 批量查询关联数据
        shift = (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id == schedule.shift_id)
        )).scalars().first()

        org = (await db.execute(
            select(OrgOrganization).where(OrgOrganization.id == schedule.org_id)
        )).scalars().first()

        leader_name = None
        if schedule.leader_staff_id:
            leader = (await db.execute(
                select(OrgStaff).where(OrgStaff.id == schedule.leader_staff_id)
            )).scalars().first()
            if leader:
                leader_name = leader.name

        detail_rows = (await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id == schedule_id)
        )).scalars().all()

        staff_map = await _get_staff_map(db, [d.staff_id for d in detail_rows])

        details = [
            {
                "id": d.id,
                "schedule_id": d.schedule_id,
                "staff_id": d.staff_id,
                "staff_name": staff_map.get(d.staff_id, "未知"),
                "role_type": d.role_type,
                "is_substitute": d.is_substitute,
                "note": d.note,
            }
            for d in detail_rows
        ]

        return {
            "id": schedule.id,
            "date": schedule.date,
            "shift_id": schedule.shift_id,
            "shift_name": getattr(shift, "name", None),
            "shift_color": getattr(shift, "color", None),
            "shift_start_time": getattr(shift, "start_time", None),
            "shift_end_time": getattr(shift, "end_time", None),
            "org_id": schedule.org_id,
            "org_name": getattr(org, "name", None),
            "leader_staff_id": schedule.leader_staff_id,
            "leader_name": leader_name,
            "status": schedule.status,
            "source": schedule.source,
            "published_at": _to_local_str(schedule.published_at),
            "published_by": schedule.published_by,
            "created_at": _to_local_str(getattr(schedule, "created_at", None)),
            "updated_at": _to_local_str(getattr(schedule, "updated_at", None)),
            "details": details,
        }

    # ==================== 创建 / 更新 / 删除 ====================

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> dict:
        """创建排班记录"""
        await _validate_schedule_refs(db, data["shift_id"], data["org_id"], data.get("leader_staff_id"))

        dup = (await db.execute(select(SchSchedule).where(
            SchSchedule.date == data["date"],
            SchSchedule.shift_id == data["shift_id"],
            SchSchedule.org_id == data["org_id"],
        ))).scalars().first()
        if dup:
            raise ValueError("该日期、班次、组织下已存在排班记录，请勿重复创建")

        schedule = SchSchedule(
            date=data["date"],
            shift_id=data["shift_id"],
            org_id=data["org_id"],
            leader_staff_id=data.get("leader_staff_id"),
            status=data.get("status", STATUS_DRAFT),
            source=data.get("source", "manual"),
        )
        db.add(schedule)
        await db.flush()
        await db.refresh(schedule)
        return await ScheduleService.get_by_id(db, schedule.id)

    @staticmethod
    async def update(db: AsyncSession, schedule_id: int, data: dict) -> dict:
        """更新排班记录"""
        schedule = await _get_writable_schedule(db, schedule_id, "修改")

        if "shift_id" in data:
            await _validate_shift_exists(db, data["shift_id"])
        if "org_id" in data:
            await _validate_org_exists(db, data["org_id"])
        if "leader_staff_id" in data and data["leader_staff_id"]:
            await _validate_staff_exists(db, data["leader_staff_id"])

        for key, value in data.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        await db.flush()
        return await ScheduleService.get_by_id(db, schedule.id)

    @staticmethod
    async def delete(db: AsyncSession, schedule_id: int) -> None:
        """删除排班记录（含级联清理调班申请）"""
        schedule = await _get_writable_schedule(db, schedule_id, "删除")

        # 清理引用该排班的调班申请（外键约束）
        from sqlalchemy import update as sa_update
        await db.execute(
            delete(SchSwapRequest).where(SchSwapRequest.requester_schedule_id == schedule_id)
        )
        await db.execute(
            sa_update(SchSwapRequest).where(
                SchSwapRequest.target_schedule_id == schedule_id
            ).values(target_schedule_id=None)
        )

        await db.delete(schedule)
        await db.flush()

    # ==================== 人员分配 ====================

    @staticmethod
    async def assign_staff(db: AsyncSession, schedule_id: int, data: dict) -> dict:
        schedule = await _get_writable_schedule(db, schedule_id, "分配人员")
        staff_id = data["staff_id"]

        if not (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first():
            raise ValueError("人员不存在")

        dup = (await db.execute(select(SchScheduleDetail).where(
            SchScheduleDetail.schedule_id == schedule_id,
            SchScheduleDetail.staff_id == staff_id,
        ))).scalars().first()
        if dup:
            raise ValueError("该人员已在此排班中，请勿重复分配")

        role_type = data.get("role_type", "member")
        if role_type == "leader":
            schedule.leader_staff_id = staff_id

        detail = SchScheduleDetail(
            schedule_id=schedule_id,
            staff_id=staff_id,
            role_type=role_type,
            is_substitute=data.get("is_substitute", False),
            note=data.get("note"),
        )
        db.add(detail)
        await db.flush()
        return {"message": "分配成功", "detail_id": detail.id}

    @staticmethod
    async def remove_staff(db: AsyncSession, schedule_id: int, staff_id: int) -> None:
        schedule = await _get_writable_schedule(db, schedule_id, "移除人员")

        detail = (await db.execute(select(SchScheduleDetail).where(
            SchScheduleDetail.schedule_id == schedule_id,
            SchScheduleDetail.staff_id == staff_id,
        ))).scalars().first()
        if not detail:
            raise ValueError("未找到对应的排班明细")

        if detail.role_type == "leader":
            schedule.leader_staff_id = None

        await db.delete(detail)
        await db.flush()

    # ==================== 批量操作 ====================

    @staticmethod
    async def batch_create_or_update(db: AsyncSession, items: list[dict]) -> int:
        """批量创建/更新排班明细"""
        schedule_ids = list({item["schedule_id"] for item in items})
        existing_result = await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
        )
        existing_by_id = {d.id: d for d in existing_result.scalars().all()}
        existing_pairs = {(d.schedule_id, d.staff_id): d for d in existing_by_id.values()}

        count = 0
        for item in items:
            item_id = item.get("id")
            if item_id and item_id in existing_by_id:
                detail = existing_by_id[item_id]
                for field in ("staff_id", "role_type", "is_substitute", "note"):
                    if field in item:
                        setattr(detail, field, item[field])
                count += 1
            else:
                pair_key = (item["schedule_id"], item["staff_id"])
                if pair_key in existing_pairs:
                    continue
                detail = SchScheduleDetail(
                    schedule_id=item["schedule_id"],
                    staff_id=item["staff_id"],
                    role_type=item.get("role_type", "member"),
                    is_substitute=item.get("is_substitute", False),
                    note=item.get("note"),
                )
                db.add(detail)
                existing_pairs[pair_key] = detail
                count += 1

        await db.flush()
        return count

    # ==================== 发布 / 审核 / 撤回 ====================

    @staticmethod
    async def publish(
        db: AsyncSession, schedule_ids: list[int], user_id: int, approval_required: bool = False,
    ) -> int:
        from datetime import datetime as dt
        schedules = await _load_schedules(db, schedule_ids)
        count = 0
        target_status = STATUS_PENDING_APPROVAL if approval_required else STATUS_PUBLISHED

        published_schedule_ids = []
        for s in schedules:
            if s.status in (STATUS_PUBLISHED, STATUS_PENDING_APPROVAL):
                continue
            s.status = target_status
            if not approval_required:
                s.published_at = dt.now()
                s.published_by = user_id
                published_schedule_ids.append(s.id)
            count += 1

        await db.flush()

        # 发布成功后，向涉及人员发送排班通知
        if not approval_required and published_schedule_ids:
            await _notify_schedule_published(db, published_schedule_ids, user_id)

        # 提交审核后，向有审核权限的人员发送审核通知
        if approval_required and count > 0:
            await _notify_schedule_pending_approval(db, schedules, user_id)

        return count

    @staticmethod
    async def approve(db: AsyncSession, schedule_ids: list[int], user_id: int) -> int:
        from datetime import datetime as dt
        schedules = await _load_schedules(db, schedule_ids)
        count = 0
        approved_schedule_ids = []
        for s in schedules:
            if s.status != STATUS_PENDING_APPROVAL:
                continue
            s.status = STATUS_PUBLISHED
            s.published_at = dt.now()
            s.published_by = user_id
            approved_schedule_ids.append(s.id)
            count += 1
        await db.flush()

        # 审核通过后，向涉及人员发送排班通知
        if approved_schedule_ids:
            await _notify_schedule_published(db, approved_schedule_ids, user_id)

        return count

    @staticmethod
    async def reject(db: AsyncSession, schedule_ids: list[int], user_id: int) -> int:
        schedules = await _load_schedules(db, schedule_ids)
        count = 0
        rejected_schedules = []
        for s in schedules:
            if s.status != STATUS_PENDING_APPROVAL:
                continue
            s.status = STATUS_DRAFT
            rejected_schedules.append(s)
            count += 1
        await db.flush()

        if not rejected_schedules:
            return count

        # 构建与发布通知一致风格的内容
        org_map = await _get_org_map(db, list({s.org_id for s in rejected_schedules}))
        shift_map = await _get_shift_map(db, {s.shift_id for s in rejected_schedules})
        detail_map, staff_map = await _get_detail_map(db, [s.id for s in rejected_schedules])

        dates = sorted({s.date for s in rejected_schedules})
        date_range = f"{dates[0]} 至 {dates[-1]}" if dates else ""
        org = org_map.get(rejected_schedules[0].org_id) if rejected_schedules else None
        org_name = getattr(org, "name", "") if org else ""

        # 按发布人分组，构建每人的排班明细
        publisher_schedules: dict[int, list[str]] = {}
        for s in rejected_schedules:
            shift = shift_map.get(s.shift_id)
            shift_name = getattr(shift, "name", "未知班次")
            date_str = str(s.date)
            pid = s.published_by
            if not pid:
                continue

            desc = f"{date_str} {shift_name}"
            for d in detail_map.get(s.id, []):
                staff_name = staff_map.get(d.staff_id, "未知")
                role_desc = "值班领导" if d.role_type == "leader" else "值班人员"
                desc += f" | {staff_name}（{role_desc}）"

            publisher_schedules.setdefault(pid, []).append(desc)

        # 通知发布人
        notified_user_ids: set[int] = set()
        for pid, desc_list in publisher_schedules.items():
            notified_user_ids.add(pid)
            detail_content = f"排班已审核未通过，已退回草稿状态：\n" + "\n".join(desc_list)
            title = f"{org_name} {date_range} 排班审核未通过" if org_name else f"{date_range} 排班审核未通过"
            await MessageService.create_message(
                db,
                receiver_id=pid,
                title=title,
                content=detail_content,
                msg_type="approve",
                sender_id=user_id,
                relation_type="schedule",
                relation_id=rejected_schedules[0].id,
            )

        # 管理员补发
        from app.services.message_service import notify_admins_extra
        summary_title = f"{org_name}排班审核已被拒绝" if org_name else f"{date_range} 排班审核已被拒绝"
        summary_content = f"{date_range} 排班审核未通过，已退回草稿状态，共 {count}条"
        await notify_admins_extra(
            db,
            title=summary_title,
            content=summary_content,
            msg_type="approve",
            sender_id=user_id,
            relation_type="schedule",
            relation_id=rejected_schedules[0].id,
            exclude_user_ids=notified_user_ids,
        )

        return count

    @staticmethod
    async def recall(db: AsyncSession, schedule_ids: list[int], user_id: int = None) -> int:
        schedules = await _load_schedules(db, schedule_ids)
        count = 0
        recalled_ids = []
        for s in schedules:
            if s.status not in (STATUS_PUBLISHED, STATUS_PENDING_APPROVAL):
                continue
            s.status = STATUS_RECALLED
            s.published_at = None
            s.published_by = None
            recalled_ids.append(s.id)
            count += 1
        await db.flush()

        # 撤回后向涉及人员发送通知
        if recalled_ids:
            await _notify_schedule_recalled(db, recalled_ids)

        return count

    @staticmethod
    async def recall_by_month(
        db: AsyncSession, org_id: int, year: int, month: int, user_id: int = None,
    ) -> int:
        """撤回指定月份的所有已发布/待审核排班。"""
        from datetime import date as dt_date
        first_day = dt_date(year, month, 1)
        if month == 12:
            last_day = dt_date(year + 1, 1, 1)
        else:
            last_day = dt_date(year, month + 1, 1)

        result = await db.execute(
            select(SchSchedule).where(
                SchSchedule.org_id == org_id,
                SchSchedule.date >= first_day,
                SchSchedule.date < last_day,
                SchSchedule.status.in_([STATUS_PUBLISHED, STATUS_PENDING_APPROVAL]),
            )
        )
        schedules = result.scalars().all()
        if not schedules:
            return 0

        count = 0
        recalled_ids = []
        for s in schedules:
            s.status = STATUS_RECALLED
            s.published_at = None
            s.published_by = None
            recalled_ids.append(s.id)
            count += 1
        await db.flush()

        if recalled_ids:
            await _notify_schedule_recalled(db, recalled_ids)

        return count

    # ==================== 人员统计 ====================

    @staticmethod
    async def get_staff_summary(db: AsyncSession, staff_id: int, days: int = 30) -> dict:
        cutoff = date.today() - timedelta(days=days)

        details = (await db.execute(
            select(SchScheduleDetail)
            .join(SchSchedule, SchScheduleDetail.schedule_id == SchSchedule.id)
            .where(SchScheduleDetail.staff_id == staff_id)
            .where(SchSchedule.date >= cutoff)
            .where(SchSchedule.status.in_([STATUS_DRAFT, STATUS_PUBLISHED]))
        )).scalars().all()

        if not details:
            return {
                "staff_id": staff_id, "total_days": 0,
                "total_hours": 0.0, "night_shifts": 0, "recent_shifts": [],
            }

        schedule_map = {
            s.id: s for s in (await db.execute(
                select(SchSchedule).where(SchSchedule.id.in_(list({d.schedule_id for d in details})))
            )).scalars().all()
        }
        shift_map = await _get_shift_map(db, {s.shift_id for s in schedule_map.values()})

        unique_dates: set = set()
        total_hours = 0.0
        night_shifts = 0
        recent_shifts: list[dict] = []

        for d in details:
            schedule = schedule_map.get(d.schedule_id)
            if not schedule:
                continue

            unique_dates.add(schedule.date)
            shift = shift_map.get(schedule.shift_id)

            if shift:
                dur = shift.effective_duration if hasattr(shift, "effective_duration") else _calc_duration(
                    shift.start_time, shift.end_time
                )
                total_hours += dur
                if _is_night_shift_time(shift.start_time, shift.end_time):
                    night_shifts += 1

            recent_shifts.append({
                "date": schedule.date,
                "shift_name": getattr(shift, "name", "未知"),
                "shift_color": getattr(shift, "color", ""),
                "start_time": getattr(shift, "start_time", ""),
                "end_time": getattr(shift, "end_time", ""),
                "role_type": d.role_type,
            })

        recent_shifts.sort(key=lambda x: x["date"], reverse=True)

        return {
            "staff_id": staff_id,
            "total_days": len(unique_dates),
            "total_hours": round(total_hours, 1),
            "night_shifts": night_shifts,
            "recent_shifts": recent_shifts,
        }

    # ==================== 工作量统计 ====================

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        *,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
        top: Optional[int] = None,
    ) -> dict:
        """获取排班工作量统计"""
        query = select(SchSchedule).where(
            SchSchedule.date >= start_date,
            SchSchedule.date <= end_date,
            SchSchedule.status == 1,
        )
        if org_id is not None:
            query = query.where(SchSchedule.org_id == org_id)

        schedules = list((await db.execute(query)).scalars().all())
        if not schedules:
            return {
                "period": {"start": str(start_date), "end": str(end_date)},
                "items": [],
                "summary": {
                    "total_staff": 0, "total_shifts": 0,
                    "avg_shifts_per_person": 0.0, "avg_hours_per_person": 0.0,
                    "total_night_shifts": 0,
                },
            }

        schedule_ids = [s.id for s in schedules]
        schedule_map = {s.id: s for s in schedules}

        # 批量查询明细
        details = list((await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
        )).scalars().all())

        shift_map = await _get_shift_map(db, {s.shift_id for s in schedules})
        org_map = await _get_org_map(db, {s.org_id for s in schedules})

        # 构建日期 → 节假日映射
        holiday_dates = _get_holiday_set(start_date, end_date)

        # 按人员聚合
        staff_data: dict[int, dict] = {}
        for d in details:
            sid = d.staff_id
            if sid not in staff_data:
                staff_data[sid] = {
                    "staff_id": sid, "total_shifts": 0,
                    "total_hours": 0.0, "night_shifts": 0,
                    "weekend_shifts": 0, "leader_shifts": 0,
                    "holiday_shifts": 0,
                }
            sd = staff_data[sid]
            sd["total_shifts"] += 1

            schedule = schedule_map.get(d.schedule_id)
            if not schedule:
                continue

            shift = shift_map.get(schedule.shift_id)
            if shift:
                dur = _calc_duration(shift.start_time, shift.end_time)
                sd["total_hours"] += dur
                if _is_night_shift_time(shift.start_time, shift.end_time):
                    sd["night_shifts"] += 1

            # 周末判断
            dow = schedule.date.weekday()
            if dow >= 5:
                sd["weekend_shifts"] += 1

            # 节假日判断
            if str(schedule.date) in holiday_dates:
                sd["holiday_shifts"] += 1

            if d.role_type == "leader":
                sd["leader_shifts"] += 1

        # 查询人员信息
        staff_ids = list(staff_data.keys())
        staff_objs = (await db.execute(
            select(OrgStaff).where(OrgStaff.id.in_(staff_ids))
        )).scalars().all()

        staff_info: dict[int, OrgStaff] = {s.id: s for s in staff_objs}

        # 构建返回数据
        items = []
        for sid, sd in staff_data.items():
            staff = staff_info.get(sid)
            staff_name = staff.name if staff else "未知"
            employee_no = getattr(staff, "employee_no", "") or ""
            org = org_map.get(staff.org_id) if staff else None
            org_name = getattr(org, "name", "") if org else ""

            weight = (
                sd["total_shifts"] * 3.0
                + sd["total_hours"] * 0.5
                + sd["night_shifts"] * 5.0
                + sd["weekend_shifts"] * 3.0
                + sd["leader_shifts"] * 3.0
                + sd["holiday_shifts"] * 4.0
            )

            items.append({
                "staff_id": sid,
                "staff_name": staff_name,
                "employee_no": employee_no,
                "org_name": org_name,
                "total_shifts": sd["total_shifts"],
                "total_hours": round(sd["total_hours"], 1),
                "night_shifts": sd["night_shifts"],
                "weekend_shifts": sd["weekend_shifts"],
                "leader_shifts": sd["leader_shifts"],
                "holiday_shifts": sd["holiday_shifts"],
                "weight_score": round(weight, 1),
            })

        items.sort(key=lambda x: x["weight_score"], reverse=True)

        if top is not None and top > 0:
            items = items[:top]

        total_staff = len(staff_data)
        all_shifts = sum(d["total_shifts"] for d in staff_data.values())
        all_hours = sum(d["total_hours"] for d in staff_data.values())
        all_night = sum(d["night_shifts"] for d in staff_data.values())
        all_holiday = sum(d["holiday_shifts"] for d in staff_data.values())

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "items": items,
            "summary": {
                "total_staff": total_staff,
                "total_shifts": all_shifts,
                "avg_shifts_per_person": round(all_shifts / total_staff, 1) if total_staff else 0.0,
                "avg_hours_per_person": round(all_hours / total_staff, 1) if total_staff else 0.0,
                "total_night_shifts": all_night,
                "total_holiday_shifts": all_holiday,
            },
        }

    # ==================== 自动排班编排 ====================

    @staticmethod
    async def auto_generate(
        db: AsyncSession,
        *,
        start_date: date,
        end_date: date,
        org_id: int,
        shift_template_ids: list[int],
        staff_ids: list[int],
        current_user_id: int,
    ) -> dict:
        """自动排班完整编排：数据准备 → 排班引擎 → 保存结果 → 返回"""
        from sqlalchemy.orm import selectinload
        from app.engine.scheduler import AutoScheduler
        from app.models.constraint import SchConstraint
        from app.models.special_rule import SchSpecialRule

        # ---- 1. 查询排班模板（含轮换组 & 值班组） ----
        shifts = await _load_shift_templates(db, shift_template_ids)

        # ---- 1.5. 收集所有模板的特殊人员池 & 领导候选池 ID（强制参与排班） ----
        special_pool_ids: set[int] = set()
        leader_pool_ids: set[int] = set()
        needs_tagged_leaders = False
        for shift in shifts:
            if getattr(shift, 'special_enabled', False) and shift.special_pool:
                special_pool_ids.update(shift.special_pool)
            if getattr(shift, 'leader_enabled', False):
                if shift.leader_pool:
                    leader_pool_ids.update(shift.leader_pool)
                else:
                    needs_tagged_leaders = True

        # 当候选池为空时，纳入全组织在职人员（引擎通过 tags / staff_tag_roles_map 自动筛选）
        tagged_leader_ids: set[int] = set()
        if needs_tagged_leaders:
            from app.models.staff import OrgStaff as OrgStaffModel
            tagged_rows = (await db.execute(
                select(OrgStaffModel.id).where(OrgStaffModel.org_id == org_id, OrgStaffModel.status == 1)
            )).scalars().all()
            tagged_leader_ids.update(tagged_rows)

        # ---- 2. 查询可用人员（含特殊池 & 领导候选池 & 标识领导人） ----
        all_staff_ids = list(set(staff_ids) | special_pool_ids | leader_pool_ids | tagged_leader_ids)
        staff_list = list((await db.execute(
            select(OrgStaff).where(OrgStaff.id.in_(all_staff_ids), OrgStaff.org_id == org_id)
        )).scalars().all())
        if not staff_list:
            raise ValueError("所选组织下无可用人员，请检查人员归属")
        effective_staff_ids = [s.id for s in staff_list]

        # ---- 3. 查询约束 & 特殊规则 ----
        constraints = list((await db.execute(
            select(SchConstraint).where(SchConstraint.enabled == True)
        )).scalars().all())
        special_rules = list((await db.execute(
            select(SchSpecialRule).where(SchSpecialRule.staff_id.in_(effective_staff_ids))
        )).scalars().all())

        # ---- 4. 处理已有排班（冲突检查 & 清理可编辑记录） ----
        await _cleanup_existing_schedules(db, org_id, start_date, end_date)

        # ---- 5. 加载历史排班（供公平性计算，读取当年度以来所有已发布数据） ----
        history_start = date(start_date.year, 1, 1)
        existing_schedules = list((await db.execute(
            select(SchSchedule).where(
                SchSchedule.org_id == org_id,
                SchSchedule.date >= history_start,
                SchSchedule.date <= end_date,
            )
        )).scalars().all())
        existing_ids = [s.id for s in existing_schedules]
        existing_details = list((await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(existing_ids))
        )).scalars().all()) if existing_ids else []

        # ---- 5.5. 加载人员标识数据（新标识体系） ----
        from app.models import OrgStaffRole, SysRole
        staff_tag_roles = list((await db.execute(
            select(OrgStaffRole).where(OrgStaffRole.staff_id.in_(effective_staff_ids))
        )).scalars().all()) if effective_staff_ids else []
        all_tag_roles = (await db.execute(
            select(SysRole).where(SysRole.role_type == "tag")
        )).scalars().all()
        tag_role_name_map = {r.id: r.name for r in all_tag_roles}
        staff_tag_roles_map: dict[int, list[str]] = defaultdict(list)
        for tr in staff_tag_roles:
            name = tag_role_name_map.get(tr.role_id)
            if name:
                staff_tag_roles_map[tr.staff_id].append(name)

        # ---- 5.6. 加载组织排班人数上限 ----
        org = (await db.execute(
            select(OrgOrganization).where(OrgOrganization.id == org_id)
        )).scalars().first()
        org_max_ratio = float(org.daily_max_scheduled_ratio) if org and org.daily_max_scheduled_ratio else None

        # ---- 5.7. 计算领导跨月轮换偏移量（ISO 周号基准） ----
        leader_offsets: dict[int, int] = {}
        for shift in shifts:
            if not getattr(shift, 'leader_enabled', False):
                continue
            earliest = (await db.execute(
                select(SchSchedule.date).where(
                    SchSchedule.shift_id == shift.id,
                    SchSchedule.leader_staff_id.isnot(None),
                ).order_by(SchSchedule.date.asc()).limit(1)
            )).scalars().first()
            if earliest:
                leader_offsets[shift.id] = earliest.isocalendar()[1]
            else:
                leader_offsets[shift.id] = start_date.isocalendar()[1]

        # ---- 6. 执行排班引擎 ----
        scheduler = AutoScheduler(
            staff_list=staff_list,
            shift_templates=shifts,
            constraints=constraints,
            special_rules=special_rules,
            existing_schedules=existing_schedules,
            existing_details=existing_details,
            staff_tag_roles_map=staff_tag_roles_map,
            org_max_ratio=org_max_ratio,
        )
        result = scheduler.generate(
            start_date=start_date,
            end_date=end_date,
            org_id=org_id,
            shift_template_ids=shift_template_ids,
            staff_ids=staff_ids,
            leader_offsets=leader_offsets,
        )

        # ---- 7. 持久化排班结果 ----
        created_schedules = []
        for sr in result["schedules"]:
            schedule = SchSchedule(
                date=date.fromisoformat(sr.date),
                shift_id=sr.shift_id,
                org_id=sr.org_id,
                leader_staff_id=sr.leader_ids[0] if sr.leader_ids else None,
                status=STATUS_DRAFT,
                source="auto",
            )
            db.add(schedule)
            await db.flush()

            leader_set = set(sr.leader_ids)
            for mid in sr.member_ids:
                db.add(SchScheduleDetail(
                    schedule_id=schedule.id,
                    staff_id=mid,
                    role_type="leader" if mid in leader_set else "member",
                ))
            created_schedules.append(schedule)

        await db.flush()

        # ---- 8. 构建返回数据 ----
        staff_name_map = {s.id: s.name for s in staff_list}
        shift_lookup = {t.id: t for t in shifts}

        schedule_data = []
        for sr, schedule in zip(result["schedules"], created_schedules):
            shift = shift_lookup.get(sr.shift_id)
            schedule_data.append({
                "schedule_id": schedule.id,
                "date": sr.date,
                "shift_id": sr.shift_id,
                "shift_name": getattr(shift, "name", ""),
                "shift_color": getattr(shift, "color", ""),
                "org_id": sr.org_id,
                "leader_ids": sr.leader_ids,
                "leader_names": [staff_name_map.get(lid, f"ID:{lid}") for lid in sr.leader_ids],
                "member_ids": sr.member_ids,
                "member_names": [staff_name_map.get(mid, f"ID:{mid}") for mid in sr.member_ids],
                "conflicts": sr.conflicts,
            })

        report = result["report"]
        report["staff_hours"] = {
            staff_name_map.get(int(sid), f"ID:{sid}"): h
            for sid, h in report.get("staff_hours", {}).items()
        }
        report["night_shift_distribution"] = {
            staff_name_map.get(int(sid), f"ID:{sid}"): c
            for sid, c in report.get("night_shift_distribution", {}).items()
        }

        return {
            "schedules": schedule_data,
            "report": report,
            "conflicts": result["conflicts"],
            "diagnostics": result.get("diagnostics", []),
        }


# ====================================================================== #
#  模块级私有辅助函数
# ====================================================================== #

def _apply_schedule_filters(query, org_id, start_date, end_date, status, shift_id):
    if org_id is not None:
        query = query.where(SchSchedule.org_id == org_id)
    if start_date:
        query = query.where(SchSchedule.date >= start_date)
    if end_date:
        query = query.where(SchSchedule.date <= end_date)
    if status is not None:
        query = query.where(SchSchedule.status == status)
    if shift_id is not None:
        query = query.where(SchSchedule.shift_id == shift_id)
    return query


def _serialize_schedule_list_item(s, shift_map, org_map, leader_map, detail_map, staff_map):
    shift = shift_map.get(s.shift_id)
    org = org_map.get(s.org_id)
    details_list = detail_map.get(s.id, [])
    return {
        "id": s.id,
        "date": s.date,
        "shift_id": s.shift_id,
        "shift_name": getattr(shift, "name", None),
        "shift_color": getattr(shift, "color", None),
        "shift_start_time": getattr(shift, "start_time", None),
        "shift_end_time": getattr(shift, "end_time", None),
        "org_id": s.org_id,
        "org_name": getattr(org, "name", None),
        "leader_staff_id": s.leader_staff_id,
        "leader_name": leader_map.get(s.leader_staff_id) if s.leader_staff_id else None,
        "status": s.status,
        "source": s.source,
        "published_at": _to_local_str(s.published_at),
        "published_by": s.published_by,
        "created_at": _to_local_str(getattr(s, "created_at", None)),
        "updated_at": _to_local_str(getattr(s, "updated_at", None)),
        "details": [
            {
                "id": d.id,
                "schedule_id": d.schedule_id,
                "staff_id": d.staff_id,
                "staff_name": staff_map.get(d.staff_id, "未知"),
                "role_type": d.role_type,
                "is_substitute": d.is_substitute,
                "note": d.note,
            }
            for d in details_list
        ],
    }


async def _validate_schedule_refs(db, shift_id, org_id, leader_id):
    if not (await db.execute(select(SchShiftTemplate).where(SchShiftTemplate.id == shift_id))).scalars().first():
        raise ValueError("班次模板不存在")
    if not (await db.execute(select(OrgOrganization).where(OrgOrganization.id == org_id))).scalars().first():
        raise ValueError("组织不存在")
    if leader_id:
        if not (await db.execute(select(OrgStaff).where(OrgStaff.id == leader_id))).scalars().first():
            raise ValueError("值班领导人员不存在")


async def _validate_shift_exists(db, shift_id):
    if not (await db.execute(select(SchShiftTemplate).where(SchShiftTemplate.id == shift_id))).scalars().first():
        raise ValueError("班次模板不存在")


async def _validate_org_exists(db, org_id):
    if not (await db.execute(select(OrgOrganization).where(OrgOrganization.id == org_id))).scalars().first():
        raise ValueError("组织不存在")


async def _validate_staff_exists(db, staff_id):
    if not (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first():
        raise ValueError("值班领导人员不存在")


async def _get_writable_schedule(db, schedule_id, action_name):
    schedule = (await db.execute(
        select(SchSchedule).where(SchSchedule.id == schedule_id)
    )).scalars().first()
    if not schedule:
        raise ValueError("排班记录不存在")
    if schedule.status in (STATUS_PUBLISHED, STATUS_PENDING_APPROVAL):
        raise ValueError(f"已发布或待审核的排班不可{action_name}，请先撤回后再操作")
    return schedule


async def _load_schedules(db, schedule_ids):
    result = await db.execute(select(SchSchedule).where(SchSchedule.id.in_(schedule_ids)))
    schedules = result.scalars().all()
    if not schedules:
        raise ValueError("未找到排班记录")
    return schedules


async def _get_shift_map(db, shift_ids):
    if not shift_ids:
        return {}
    result = await db.execute(select(SchShiftTemplate).where(SchShiftTemplate.id.in_(list(shift_ids))))
    return {s.id: s for s in result.scalars().all()}


async def _get_org_map(db, org_ids):
    if not org_ids:
        return {}
    result = await db.execute(select(OrgOrganization).where(OrgOrganization.id.in_(list(org_ids))))
    return {o.id: o for o in result.scalars().all()}


async def _get_staff_map(db, staff_ids) -> dict[int, str]:
    if not staff_ids:
        return {}
    result = await db.execute(select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(staff_ids)))
    return {row[0]: row[1] for row in result.all()}


async def _get_detail_map(db, schedule_ids):
    if not schedule_ids:
        return {}, {}
    details = (await db.execute(
        select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
    )).scalars().all()

    detail_map: dict[int, list] = {}
    all_staff_ids: set[int] = set()
    for d in details:
        detail_map.setdefault(d.schedule_id, []).append(d)
        all_staff_ids.add(d.staff_id)

    staff_map = await _get_staff_map(db, list(all_staff_ids))
    return detail_map, staff_map


async def _load_shift_templates(db, shift_template_ids):
    """加载班次模板及其关联的值班组。"""
    try:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(SchShiftTemplate)
            .options(
                selectinload(SchShiftTemplate.duty_teams),
            )
            .where(SchShiftTemplate.id.in_(shift_template_ids))
        )
        return list(result.scalars().all())
    except Exception:
        result = await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_template_ids))
        )
        shifts = list(result.scalars().all())
        for t in shifts:
            t.duty_teams = []
        return shifts


async def _cleanup_existing_schedules(db, org_id, start_date, end_date):
    """检查并清理已有排班。已发布/待审核的记录会阻止自动排班。"""
    existing = list((await db.execute(
        select(SchSchedule).where(
            SchSchedule.org_id == org_id,
            SchSchedule.date >= start_date,
            SchSchedule.date <= end_date,
        )
    )).scalars().all())

    if not existing:
        return

    locked_count = sum(1 for s in existing if s.status in SchSchedule.LOCKED_STATUSES)
    if locked_count > 0:
        raise ValueError(f"该日期范围内存在 {locked_count} 条已发布或待审核排班，请先撤回后再自动生成")

    delete_ids = [s.id for s in existing if s.status in SchSchedule.EDITABLE_STATUSES]
    if delete_ids:
        # 清理关联的调班申请（外键约束）
        await db.execute(delete(SchSwapRequest).where(SchSwapRequest.requester_schedule_id.in_(delete_ids)))
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(SchSwapRequest).where(
                SchSwapRequest.target_schedule_id.in_(delete_ids)
            ).values(target_schedule_id=None)
        )
        await db.execute(delete(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(delete_ids)))
        await db.execute(delete(SchSchedule).where(SchSchedule.id.in_(delete_ids)))
        await db.flush()


def _calc_duration(start_time: str, end_time: str) -> float:
    try:
        sh, sm = map(int, start_time.split(":"))
        eh, em = map(int, end_time.split(":"))
        dur = (eh * 60 + em - sh * 60 - sm) / 60
        return dur + 24 if dur <= 0 else dur
    except (ValueError, AttributeError):
        return 0.0


def _is_night_shift_time(start_time: str, end_time: str) -> bool:
    try:
        sh, _ = map(int, start_time.split(":"))
        eh, _ = map(int, end_time.split(":"))
        return sh >= 20 or eh <= 8
    except (ValueError, AttributeError):
        return False


def _get_holiday_set(start_date: date, end_date: date) -> set[str]:
    """获取日期范围内的法定节假日日期集合（使用 chinese_calendar 库，如果不可用则使用内置规则）"""
    holidays: set[str] = set()
    try:
        from chinese_calendar import is_holiday, get_holiday_detail
        current = start_date
        while current <= end_date:
            if is_holiday(current):
                holidays.add(str(current))
            current += timedelta(days=1)
    except ImportError:
        # chinese_calendar 未安装，使用周末近似
        current = start_date
        while current <= end_date:
            if current.weekday() >= 5:  # 周六、周日
                holidays.add(str(current))
            current += timedelta(days=1)
    return holidays


# ====================================================================== #
#  排班通知辅助函数
# ====================================================================== #

async def _notify_schedule_published(db: AsyncSession, schedule_ids: list[int], publisher_id: int):
    """排班发布后，向涉及的所有人员发送排班通知"""
    from app.models import OrgStaff, SysUser
    from app.services.message_service import notify_admins_extra

    schedules = list((await db.execute(
        select(SchSchedule).where(SchSchedule.id.in_(schedule_ids))
    )).scalars().all())
    if not schedules:
        return

    detail_map, staff_map = await _get_detail_map(db, schedule_ids)

    # 收集所有涉及的人员 staff_id（包括领导和成员）
    all_staff_ids: set[int] = set()
    for s in schedules:
        if s.leader_staff_id:
            all_staff_ids.add(s.leader_staff_id)
        for d in detail_map.get(s.id, []):
            all_staff_ids.add(d.staff_id)

    if not all_staff_ids:
        return

    # staff_id → user_id（关系方向：SysUser.staff_id → OrgStaff.id，所以查 SysUser 表）
    user_rows = (await db.execute(
        select(SysUser.staff_id, SysUser.id)
        .where(SysUser.staff_id.in_(list(all_staff_ids)), SysUser.status == 1)
    )).all()
    staff_to_user: dict[int, int] = {row[0]: row[1] for row in user_rows if row[0]}

    # 按组织分组，构建通知内容
    shift_map = await _get_shift_map(db, {s.shift_id for s in schedules})
    org_map = await _get_org_map(db, list({s.org_id for s in schedules}))

    # 日期范围
    dates = sorted({s.date for s in schedules})
    date_range = f"{dates[0]} 至 {dates[-1]}" if dates else ""

    # 构建每人自己的排班明细
    person_schedules: dict[int, list[str]] = {}
    for s in schedules:
        shift = shift_map.get(s.shift_id)
        shift_name = getattr(shift, "name", "未知班次")
        date_str = str(s.date)
        for d in detail_map.get(s.id, []):
            role_desc = "值班领导" if d.role_type == "leader" else "值班人员"
            desc = f"{date_str} {shift_name}（{role_desc}）"
            person_schedules.setdefault(d.staff_id, []).append(desc)

    # 给每人发通知
    org = org_map.get(schedules[0].org_id)
    org_name = getattr(org, "name", "") if org else ""

    notified_user_ids: set[int] = set()
    for staff_id, desc_list in person_schedules.items():
        user_id = staff_to_user.get(staff_id)
        if not user_id:
            continue
        notified_user_ids.add(user_id)
        content = f"您在 {date_range} 的排班已发布：\n" + "\n".join(desc_list)
        await MessageService.create_message(
            db,
            receiver_id=user_id,
            title=f"{org_name}排班表已发布，请查看您的值班安排" if org_name else "排班表已发布，请查看您的值班安排",
            content=content,
            msg_type="schedule",
            sender_id=publisher_id,
            relation_type="schedule",
            relation_id=schedule_ids[0],
        )

    # 管理员接收全部通知开关开启时，给未收到通知的管理员补发
    summary_content = f"{date_range} 排班已发布，共 {len(schedules)} 条。"
    await notify_admins_extra(
        db,
        title=f"{org_name}排班表已发布" if org_name else "排班表已发布",
        content=summary_content,
        msg_type="schedule",
        sender_id=publisher_id,
        relation_type="schedule",
        relation_id=schedule_ids[0],
        exclude_user_ids=notified_user_ids,
    )


async def _notify_schedule_pending_approval(db: AsyncSession, schedules: list, submitter_id: int):
    """排班提交审核后，向有审核权限的人员发送审核通知"""
    from app.models import SysUser, SysUserRole, SysRole
    from app.services.message_service import notify_admins_extra

    scheduler_roles = (await db.execute(
        select(SysRole).where(SysRole.code.in_(["admin", "scheduler"]))
    )).scalars().all()

    if not scheduler_roles:
        return

    role_ids = [r.id for r in scheduler_roles]
    user_roles = (await db.execute(
        select(SysUserRole.user_id)
        .where(SysUserRole.role_id.in_(role_ids))
        .distinct()
    )).all()

    approver_user_ids = list({row[0] for row in user_roles if row[0]})

    # 排除提交人自己
    approver_user_ids = [uid for uid in approver_user_ids if uid != submitter_id]

    dates = sorted({s.date for s in schedules})
    date_range = f"{dates[0]} 至 {dates[-1]}" if dates else ""

    org_map = await _get_org_map(db, list({s.org_id for s in schedules}))
    org = org_map.get(schedules[0].org_id) if schedules else None
    org_name = getattr(org, "name", "") if org else ""

    title = "有新的排班待审核"
    content = f"{org_name}的 {date_range} 排班已提交审核，共 {len(schedules)} 条，请及时处理。" if org_name else f"{date_range} 排班已提交审核，共 {len(schedules)} 条，请及时处理。"

    notified_user_ids: set[int] = set()
    for uid in approver_user_ids:
        notified_user_ids.add(uid)
        await MessageService.create_message(
            db,
            receiver_id=uid,
            title=title,
            content=content,
            msg_type="approve",
            sender_id=submitter_id,
            relation_type="schedule",
            relation_id=schedules[0].id if schedules else None,
        )

    # 管理员接收全部通知开关开启时，给被排除的管理员补发（如提交人即管理员的情况）
    await notify_admins_extra(
        db,
        title=title,
        content=content,
        msg_type="approve",
        sender_id=submitter_id,
        relation_type="schedule",
        relation_id=schedules[0].id if schedules else None,
        exclude_user_ids=notified_user_ids,
    )


async def _notify_schedule_recalled(db: AsyncSession, schedule_ids: list[int]):
    """排班撤回后，向涉及人员发送通知"""
    from app.models import SysUser
    from app.services.message_service import notify_admins_extra

    schedules = list((await db.execute(
        select(SchSchedule).where(SchSchedule.id.in_(schedule_ids))
    )).scalars().all())
    if not schedules:
        return

    detail_map, _ = await _get_detail_map(db, schedule_ids)

    all_staff_ids: set[int] = set()
    for s in schedules:
        if s.leader_staff_id:
            all_staff_ids.add(s.leader_staff_id)
        for d in detail_map.get(s.id, []):
            all_staff_ids.add(d.staff_id)

    if not all_staff_ids:
        return

    # staff_id → user_id（反向查 SysUser 表）
    user_rows = (await db.execute(
        select(SysUser.staff_id, SysUser.id)
        .where(SysUser.staff_id.in_(list(all_staff_ids)), SysUser.status == 1)
    )).all()
    staff_to_user: dict[int, int] = {row[0]: row[1] for row in user_rows if row[0]}

    dates = sorted({s.date for s in schedules})
    date_range = f"{dates[0]} 至 {dates[-1]}" if dates else ""

    org_map = await _get_org_map(db, list({s.org_id for s in schedules}))
    org = org_map.get(schedules[0].org_id) if schedules else None
    org_name = getattr(org, "name", "") if org else ""

    notified_user_ids: set[int] = set()
    for staff_id, user_id in staff_to_user.items():
        if user_id in notified_user_ids:
            continue
        notified_user_ids.add(user_id)
        await MessageService.create_message(
            db,
            receiver_id=user_id,
            title=f"{org_name}排班表已撤回" if org_name else "排班表已撤回",
            content=f"{date_range} 的排班表已撤回，请等待重新发布。",
            msg_type="schedule",
            relation_type="schedule",
            relation_id=schedule_ids[0],
        )

    # 管理员接收全部通知开关开启时，给未收到通知的管理员补发
    await notify_admins_extra(
        db,
        title=f"{org_name}排班表已撤回" if org_name else "排班表已撤回",
        content=f"{date_range} 的排班表已撤回，请等待重新发布。",
        msg_type="schedule",
        relation_type="schedule",
        relation_id=schedule_ids[0],
        exclude_user_ids=notified_user_ids,
    )
