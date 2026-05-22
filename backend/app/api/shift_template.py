from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models import SysUser
from app.schemas.shift_template import (
    ShiftTemplateCreate,
    ShiftTemplateUpdate,
    ShiftTemplateResponse,
)
from app.services.shift_template_service import ShiftTemplateService

router = APIRouter(prefix="/shift-templates", tags=["班次模板管理"])


@router.get("", response_model=list[ShiftTemplateResponse])
async def list_shift_templates(
    org_id: Optional[int] = Query(None, description="组织ID筛选"),
    status: Optional[int] = Query(None, description="状态筛选：0=停用 1=启用"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "read")),
):
    """获取班次模板列表"""
    templates = await ShiftTemplateService.list_templates(db, org_id=org_id, status=status, keyword=keyword)
    return templates


# ==================== 选项数据（供排班等页面下拉使用，只需登录权限） ====================

@router.get("/options", summary="获取班次模板选项列表")
async def get_shift_template_options(
    org_id: Optional[int] = Query(None, description="组织ID筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取启用状态的班次模板选项（仅返回下拉所需字段，无需额外权限）"""
    from app.models.shift_template import SchShiftTemplate
    stmt = (
        select(SchShiftTemplate)
        .where(SchShiftTemplate.status == 1)
        .order_by(SchShiftTemplate.id)
    )
    if org_id is not None:
        stmt = stmt.where(
            (SchShiftTemplate.org_id == org_id) | (SchShiftTemplate.org_id.is_(None))
        )
    result = await db.execute(stmt)
    templates = result.scalars().all()
    data = [
        {
            "id": t.id,
            "name": t.name,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "color": t.color,
        }
        for t in templates
    ]
    return {"code": 200, "data": data, "message": "success"}


@router.get("/{template_id}", response_model=ShiftTemplateResponse)
async def get_shift_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "read")),
):
    """获取单个班次模板详情"""
    template = await ShiftTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="班次模板不存在")
    return template


@router.post("", response_model=ShiftTemplateResponse, status_code=201)
async def create_shift_template(
    data: ShiftTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "create")),
):
    """创建班次模板"""
    try:
        template = await ShiftTemplateService.create_template(db, data)
        return template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{template_id}", response_model=ShiftTemplateResponse)
async def update_shift_template(
    template_id: int,
    data: ShiftTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    """更新班次模板"""
    try:
        template = await ShiftTemplateService.update_template(db, template_id, data)
        return template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{template_id}")
async def delete_shift_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "delete")),
):
    """删除班次模板"""
    try:
        await ShiftTemplateService.delete_template(db, template_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{template_id}/copy", response_model=ShiftTemplateResponse)
async def copy_shift_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "create")),
):
    """复制班次模板"""
    try:
        template = await ShiftTemplateService.copy_template(db, template_id)
        return template
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")


@router.put("/{template_id}/status", response_model=ShiftTemplateResponse)
async def toggle_shift_template_status(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    """启用/停用班次模板"""
    try:
        template = await ShiftTemplateService.toggle_status(db, template_id)
        return template
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")

import json
from app.models.shift_template import SchRotationGroup
from app.schemas.shift_template import RotationGroupCreate, RotationGroupResponse


@router.get("/{template_id}/rotation-groups", summary="获取轮换组列表")
async def get_rotation_groups(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "read")),
):
    result = await db.execute(
        select(SchRotationGroup).where(
            SchRotationGroup.shift_template_id == template_id
        ).order_by(SchRotationGroup.priority)
    )
    groups = result.scalars().all()
    return [
        RotationGroupResponse(
            id=g.id,
            shift_template_id=g.shift_template_id,
            name=g.name,
            staff_ids=json.loads(g.staff_ids) if g.staff_ids else [],
            rotation_unit=g.rotation_unit,
            slot_count=g.slot_count,
            priority=g.priority,
            enabled=bool(g.enabled),
        )
        for g in groups
    ]


@router.post("/{template_id}/rotation-groups", summary="创建轮换组")
async def create_rotation_group(
    template_id: int,
    data: RotationGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    group = SchRotationGroup(
        shift_template_id=template_id,
        name=data.name,
        staff_ids=json.dumps(data.staff_ids),
        rotation_unit=data.rotation_unit,
        slot_count=data.slot_count,
        priority=data.priority,
        enabled=1 if data.enabled else 0,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return RotationGroupResponse(
        id=group.id,
        shift_template_id=group.shift_template_id,
        name=group.name,
        staff_ids=data.staff_ids,
        rotation_unit=group.rotation_unit,
        slot_count=group.slot_count,
        priority=group.priority,
        enabled=data.enabled,
    )


@router.put("/{template_id}/rotation-groups/{group_id}", summary="更新轮换组")
async def update_rotation_group(
    template_id: int,
    group_id: int,
    data: RotationGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    result = await db.execute(
        select(SchRotationGroup).where(
            SchRotationGroup.id == group_id,
            SchRotationGroup.shift_template_id == template_id,
        )
    )
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="轮换组不存在")

    group.name = data.name
    group.staff_ids = json.dumps(data.staff_ids)
    group.rotation_unit = data.rotation_unit
    group.slot_count = data.slot_count
    group.priority = data.priority
    group.enabled = 1 if data.enabled else 0
    await db.flush()

    return RotationGroupResponse(
        id=group.id,
        shift_template_id=group.shift_template_id,
        name=group.name,
        staff_ids=data.staff_ids,
        rotation_unit=group.rotation_unit,
        slot_count=group.slot_count,
        priority=group.priority,
        enabled=data.enabled,
    )


@router.delete("/{template_id}/rotation-groups/{group_id}", summary="删除轮换组")
async def delete_rotation_group(
    template_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "delete")),
):
    result = await db.execute(
        select(SchRotationGroup).where(
            SchRotationGroup.id == group_id,
            SchRotationGroup.shift_template_id == template_id,
        )
    )
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="轮换组不存在")

    await db.delete(group)
    await db.flush()
    return {"message": "删除成功"}
from app.models.duty_team import SchDutyTeam
from app.schemas.shift_template import DutyTeamCreate, DutyTeamResponse


@router.get("/{template_id}/duty-teams", summary="获取值班组列表")
async def get_duty_teams(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "read")),
):
    result = await db.execute(
        select(SchDutyTeam).where(
            SchDutyTeam.shift_template_id == template_id
        ).order_by(SchDutyTeam.priority)
    )
    teams = result.scalars().all()
    return [
        DutyTeamResponse(
            id=t.id,
            shift_template_id=t.shift_template_id,
            name=t.name,
            staff_ids=json.loads(t.staff_ids) if t.staff_ids else [],
            priority=t.priority,
            enabled=bool(t.enabled),
        )
        for t in teams
    ]


@router.post("/{template_id}/duty-teams", summary="创建值班组")
async def create_duty_team(
    template_id: int,
    data: DutyTeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    team = SchDutyTeam(
        shift_template_id=template_id,
        name=data.name,
        staff_ids=json.dumps(data.staff_ids),
        priority=data.priority,
        enabled=1 if data.enabled else 0,
    )
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return DutyTeamResponse(
        id=team.id,
        shift_template_id=team.shift_template_id,
        name=team.name,
        staff_ids=data.staff_ids,
        priority=team.priority,
        enabled=data.enabled,
    )


@router.put("/{template_id}/duty-teams/{team_id}", summary="更新值班组")
async def update_duty_team(
    template_id: int,
    team_id: int,
    data: DutyTeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "update")),
):
    result = await db.execute(
        select(SchDutyTeam).where(
            SchDutyTeam.id == team_id,
            SchDutyTeam.shift_template_id == template_id,
        )
    )
    team = result.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="值班组不存在")

    team.name = data.name
    team.staff_ids = json.dumps(data.staff_ids)
    team.priority = data.priority
    team.enabled = 1 if data.enabled else 0
    await db.flush()

    return DutyTeamResponse(
        id=team.id,
        shift_template_id=team.shift_template_id,
        name=team.name,
        staff_ids=data.staff_ids,
        priority=team.priority,
        enabled=data.enabled,
    )


@router.delete("/{template_id}/duty-teams/{team_id}", summary="删除值班组")
async def delete_duty_team(
    template_id: int,
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("shift_template", "delete")),
):
    result = await db.execute(
        select(SchDutyTeam).where(
            SchDutyTeam.id == team_id,
            SchDutyTeam.shift_template_id == template_id,
        )
    )
    team = result.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="值班组不存在")

    await db.delete(team)
    await db.flush()
    return {"message": "删除成功"}
