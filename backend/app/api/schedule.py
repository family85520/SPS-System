"""排班管理 API 路由"""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.auth import get_current_user
from app.api.deps import require_permissions
from app.models import SysUser, OrgStaff
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.schemas.schedule import (
    AssignStaffRequest,
    BatchDetailRequest,
    BatchPublishRequest,
    CalendarResponse,
    RemoveStaffRequest,
    ScheduleCreate,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdate,
    StaffSummaryResponse,
)
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["排班管理"])


# ==================== 排班列表 + 日历 ====================

@router.get("", response_model=ScheduleListResponse, summary="获取排班列表")
async def list_schedules(
    org_id: int | None = Query(None, description="组织ID筛选"),
    staff_id: int | None = Query(None, description="人员ID筛选（查该人员参与的排班）"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    status: int | None = Query(None, description="状态：0草稿/1已发布/2已撤回"),
    shift_id: int | None = Query(None, description="班次模板ID筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    sd = _parse_date(start_date, "start_date") if start_date else None
    ed = _parse_date(end_date, "end_date") if end_date else None
    result = await ScheduleService.get_list(
        db, org_id=org_id, staff_id=staff_id, start_date=sd, end_date=ed,
        status=status, shift_id=shift_id, page=page, page_size=page_size,
    )
    return ScheduleListResponse(items=result["items"], total=result["total"])


@router.get("/calendar", response_model=CalendarResponse, summary="获取排班日历数据")
async def get_schedule_calendar(
    start_date: str = Query(..., description="日历起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="日历结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID筛选"),
    status: int | None = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    result = await ScheduleService.get_calendar(
        db, start_date=_parse_date(start_date, "start_date"),
        end_date=_parse_date(end_date, "end_date"), org_id=org_id, status=status,
    )
    return CalendarResponse(dates=result["dates"])


# ==================== 轻量选项接口（登录即可，供调班等页面下拉使用） ====================

@router.get("/by-staff", summary="获取指定人员的排班列表（选项用）")
async def get_schedules_by_staff(
    staff_id: int = Query(..., description="人员ID"),
    status: int | None = Query(None, description="状态筛选：0草稿/1已发布"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取指定人员参与的排班列表（仅返回下拉所需字段，无需 schedule.read 权限）"""
    # 查找该人员作为 detail 的所有 schedule_id
    detail_query = select(SchScheduleDetail.schedule_id).where(
        SchScheduleDetail.staff_id == staff_id
    )
    detail_result = await db.execute(detail_query)
    schedule_ids = [row[0] for row in detail_result.all()]

    if not schedule_ids:
        return {"code": 200, "data": [], "message": "success"}

    query = select(SchSchedule).where(SchSchedule.id.in_(schedule_ids))
    if status is not None:
        query = query.where(SchSchedule.status == status)
    query = query.order_by(SchSchedule.date.desc()).limit(100)

    schedules = (await db.execute(query)).scalars().all()

    # 批量查班次名称
    from app.models.shift_template import SchShiftTemplate
    shift_ids = list({s.shift_id for s in schedules})
    shift_map: dict[int, str] = {}
    if shift_ids:
        shifts = (await db.execute(
            select(SchShiftTemplate.id, SchShiftTemplate.name)
            .where(SchShiftTemplate.id.in_(shift_ids))
        )).all()
        shift_map = {row[0]: row[1] for row in shifts}

    data = [
        {
            "id": s.id,
            "date": str(s.date),
            "shift_id": s.shift_id,
            "shift_name": shift_map.get(s.shift_id, ""),
            "status": s.status,
            "org_id": s.org_id,
        }
        for s in schedules
    ]
    return {"code": 200, "data": data, "message": "success"}


# ==================== 工作量统计（必须在 /{schedule_id} 之前，避免路由冲突） ====================

@router.get("/statistics", summary="排班工作量统计")
async def get_schedule_statistics(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID筛选"),
    top: int | None = Query(None, ge=1, description="仅返回前N名"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    result = await ScheduleService.get_statistics(
        db,
        start_date=_parse_date(start_date, "start_date"),
        end_date=_parse_date(end_date, "end_date"),
        org_id=org_id,
        top=top,
    )
    return result


# ==================== 单条 CRUD ====================

@router.get("/{schedule_id}", response_model=ScheduleResponse, summary="获取排班详情")
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    try:
        return await ScheduleService.get_by_id(db, schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=ScheduleResponse, status_code=201, summary="创建排班")
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "create")),
):
    try:
        return await ScheduleService.create(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{schedule_id}", response_model=ScheduleResponse, summary="更新排班")
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "update")),
):
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="未提供任何更新字段")
    try:
        return await ScheduleService.update(db, schedule_id, update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{schedule_id}", summary="删除排班")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "delete")),
):
    try:
        await ScheduleService.delete(db, schedule_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 人员分配 ====================

@router.post("/{schedule_id}/assign-staff", summary="分配人员")
async def assign_staff(
    schedule_id: int,
    data: AssignStaffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "update")),
):
    try:
        return await ScheduleService.assign_staff(db, schedule_id, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{schedule_id}/remove-staff", summary="移除人员")
async def remove_staff(
    schedule_id: int,
    data: RemoveStaffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "update")),
):
    try:
        await ScheduleService.remove_staff(db, schedule_id, data.staff_id)
        return {"message": "移除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 批量操作 ====================

@router.post("/batch", summary="批量创建/更新排班明细")
async def batch_detail(
    data: BatchDetailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "create")),
):
    if not data.items:
        raise HTTPException(status_code=400, detail="明细列表不能为空")
    try:
        count = await ScheduleService.batch_create_or_update(
            db, [item.model_dump() for item in data.items]
        )
        return {"message": f"成功处理 {count} 条记录", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 发布 / 撤回 / 审核 ====================

@router.post("/publish", summary="发布排班")
async def publish_schedules(
    data: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "publish")),
):
    try:
        from app.models.audit_log import SysConfig
        config = (await db.execute(
            select(SysConfig).where(SysConfig.config_key == "schedule_approval_enabled")
        )).scalars().first()
        approval_required = config and config.config_value == "true"

        count = await ScheduleService.publish(
            db, data.schedule_ids, current_user.id, approval_required=approval_required,
        )
        if approval_required:
            return {"message": f"已提交 {count} 条排班等待审核", "count": count, "need_approval": True}
        return {"message": f"成功发布 {count} 条排班", "count": count, "need_approval": False}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approve", summary="审核通过排班")  # 修复：原代码缺少 @router.post 装饰器
async def approve_schedules(
    data: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "approve")),
):
    try:
        count = await ScheduleService.approve(db, data.schedule_ids, current_user.id)
        return {"message": f"审核通过 {count} 条排班", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject", summary="审核拒绝排班")
async def reject_schedules(
    data: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "approve")),
):
    try:
        count = await ScheduleService.reject(db, data.schedule_ids, current_user.id)
        return {"message": f"已拒绝 {count} 条排班，已打回草稿", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recall", summary="撤回排班（按ID）")
async def recall_schedules(
    data: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "publish")),
):
    try:
        count = await ScheduleService.recall(db, data.schedule_ids, current_user.id)
        return {"message": f"成功撤回 {count} 条排班", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recall-month", summary="按月撤回排班")
async def recall_schedules_by_month(
    org_id: int = Query(..., description="组织ID"),
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份 1-12"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "publish")),
):
    try:
        count = await ScheduleService.recall_by_month(db, org_id, year, month, current_user.id)
        return {"message": f"成功撤回 {count} 条排班", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete-drafts", summary="一键删除草稿排班")
async def delete_draft_schedules(
    org_id: int | None = Query(None, description="组织ID（可选）"),
    start_date: str | None = Query(None, description="起始日期（可选）"),
    end_date: str | None = Query(None, description="结束日期（可选）"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "delete")),
):
    from app.models.swap import SchSwapRequest

    try:
        query = select(SchSchedule).where(SchSchedule.status.in_([0, 2]))
        if org_id is not None:
            query = query.where(SchSchedule.org_id == org_id)
        if start_date:
            query = query.where(SchSchedule.date >= _parse_date(start_date, "start_date"))
        if end_date:
            query = query.where(SchSchedule.date <= _parse_date(end_date, "end_date"))

        schedules = list((await db.execute(query)).scalars().all())
        if not schedules:
            return {"message": "没有可删除的草稿排班", "count": 0}

        schedule_ids = [s.id for s in schedules]

        # 1. 清理关联的调班申请（外键约束：sch_swap_request → sch_schedule）
        await db.execute(
            delete(SchSwapRequest).where(SchSwapRequest.requester_schedule_id.in_(schedule_ids))
        )
        await db.execute(
            delete(SchSwapRequest).where(SchSwapRequest.target_schedule_id.in_(schedule_ids))
        )

        # 2. 清理排班明细
        await db.execute(
            delete(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
        )

        # 3. 清理排班主记录
        await db.execute(
            delete(SchSchedule).where(SchSchedule.id.in_(schedule_ids))
        )
        await db.flush()

        return {"message": f"已删除 {len(schedule_ids)} 条草稿排班", "count": len(schedule_ids)}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除草稿排班失败：{str(e)}")


# ==================== 人员统计 ====================

@router.get(
    "/staff-summary/{staff_id}", response_model=StaffSummaryResponse, summary="人员排班统计",
)
async def get_staff_summary(
    staff_id: int,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    result = await ScheduleService.get_staff_summary(db, staff_id, days)
    return StaffSummaryResponse(**result)


# ==================== 自动排班 ====================

@router.post("/auto-generate", summary="自动排班生成")
async def auto_generate_schedule(
    start_date: str = Query(..., description="排班起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="排班结束日期 YYYY-MM-DD"),
    org_id: int = Query(..., description="组织ID"),
    shift_template_ids: str = Query(..., description="班次模板ID列表，逗号分隔"),
    staff_ids: str = Query(..., description="人员ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "create")),
):
    """自动生成排班表"""
    sd = _parse_date(start_date, "start_date")
    ed = _parse_date(end_date, "end_date")
    if ed < sd:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")

    s_ids = _parse_ids(shift_template_ids, "班次模板")
    st_ids = _parse_ids(staff_ids, "人员")

    try:
        return await ScheduleService.auto_generate(
            db,
            start_date=sd,
            end_date=ed,
            org_id=org_id,
            shift_template_ids=s_ids,
            staff_ids=st_ids,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 约束校验 ====================

@router.post("/validate", summary="全局约束校验")
async def validate_schedules(
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    from app.models.constraint import SchConstraint
    from app.models.special_rule import SchSpecialRule
    from app.models.shift_template import SchShiftTemplate
    from app.engine.constraint_checker import ConstraintChecker

    sd = _parse_date(start_date, "start_date")
    ed = _parse_date(end_date, "end_date")

    query = select(SchSchedule).where(SchSchedule.date >= sd, SchSchedule.date <= ed)
    if org_id is not None:
        query = query.where(SchSchedule.org_id == org_id)

    schedules = list((await db.execute(query)).scalars().all())
    if not schedules:
        return {
            "passed_count": 0, "warning_count": 0, "failed_count": 0,
            "is_valid": True, "passed": [], "warnings": [], "failed": [],
        }

    schedule_ids = [s.id for s in schedules]
    details = list((await db.execute(
        select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
    )).scalars().all())

    constraints = list((await db.execute(select(SchConstraint))).scalars().all())
    staff_ids = list({d.staff_id for d in details})
    special_rules = list((await db.execute(
        select(SchSpecialRule).where(SchSpecialRule.staff_id.in_(staff_ids))
    )).scalars().all())

    shift_ids = list({s.shift_id for s in schedules})
    shifts = {
        s.id: s for s in (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_ids))
        )).scalars().all()
    }

    staff_map = {
        row[0]: row[1] for row in (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(staff_ids))
        )).all()
    }

    checker = ConstraintChecker(schedules, details, constraints, special_rules, shifts, staff_map)
    return checker.check_all(scope_org_id=org_id).to_dict()


@router.post("/validate-single", summary="单条排班实时校验")
async def validate_single_schedule(
    schedule_id: int = Query(..., description="排班记录ID"),
    staff_id: int = Query(..., description="人员ID"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("schedule", "read")),
):
    from app.models.constraint import SchConstraint
    from app.models.special_rule import SchSpecialRule
    from app.models.shift_template import SchShiftTemplate
    from app.engine.constraint_checker import ConstraintChecker

    schedule = (await db.execute(
        select(SchSchedule).where(SchSchedule.id == schedule_id)
    )).scalars().first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")

    details = list((await db.execute(
        select(SchScheduleDetail).where(SchScheduleDetail.staff_id == staff_id)
    )).scalars().all())

    related_ids = list({d.schedule_id for d in details})
    if schedule_id not in related_ids:
        related_ids.append(schedule_id)

    schedules = list((await db.execute(
        select(SchSchedule).where(SchSchedule.id.in_(related_ids))
    )).scalars().all())

    constraints = list((await db.execute(select(SchConstraint))).scalars().all())
    special_rules = list((await db.execute(
        select(SchSpecialRule).where(SchSpecialRule.staff_id == staff_id)
    )).scalars().all())

    shift_ids = list({s.shift_id for s in schedules})
    if schedule.shift_id not in shift_ids:
        shift_ids.append(schedule.shift_id)
    shifts = {
        s.id: s for s in (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_ids))
        )).scalars().all()
    }

    staff_map = {
        row[0]: row[1] for row in (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id == staff_id)
        )).all()
    }

    checker = ConstraintChecker(schedules, details, constraints, special_rules, shifts, staff_map)
    violations = checker.check_single(
        schedule_id=schedule_id, staff_id=staff_id,
        schedule_date=str(schedule.date), shift_id=schedule.shift_id,
    )

    return {
        "is_valid": len(violations) == 0,
        "violations": [
            {
                "rule_type": v.rule_type, "rule_name": v.rule_name,
                "message": v.message, "schedule_id": v.schedule_id,
                "staff_id": v.staff_id, "date": v.date, "severity": v.severity,
            }
            for v in violations
        ],
    }


# ==================== 工具函数 ====================

def _parse_date(date_str: str, field_name: str) -> date_type:
    try:
        return date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} 格式错误，应为 YYYY-MM-DD")


def _parse_ids(raw: str, label: str) -> list[int]:
    """解析逗号分隔的 ID 字符串。"""
    ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail=f"请选择至少一个{label}")
    return ids
