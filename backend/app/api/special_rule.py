from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from app.database import get_db
from app.api.auth import get_current_user
from app.api.deps import require_permissions
from app.models import SysUser
from app.models.special_rule import SchSpecialRule
from app.schemas.special_rule import (
    SpecialRuleCreate,
    SpecialRuleUpdate,
    SpecialRuleResponse,
)
from app.services.special_rule_service import SpecialRuleService

router = APIRouter(prefix="/special-rules", tags=["特殊排班规则管理"])


@router.get("", response_model=list[SpecialRuleResponse])
async def list_special_rules(
    staff_id: Optional[int] = Query(None, description="按人员ID筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("constraint", "read")),
):
    """获取特殊规则列表"""
    return await SpecialRuleService.list_rules(db, staff_id=staff_id)


@router.get("/{rule_id}", response_model=SpecialRuleResponse)
async def get_special_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("constraint", "read")),
):
    """获取单个特殊规则详情"""
    rule = await SpecialRuleService.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="特殊规则不存在")
    return rule


@router.post("", response_model=SpecialRuleResponse, status_code=201)
async def create_special_rule(
    data: SpecialRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("constraint", "create")),
):
    """创建特殊规则"""
    # ===== 业务规则校验 =====
    error_msg = await _validate_special_rule(db, data.staff_id, data.rule_type, data.params)
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        return await SpecialRuleService.create_rule(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{rule_id}", response_model=SpecialRuleResponse)
async def update_special_rule(
    rule_id: int,
    data: SpecialRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("constraint", "update")),
):
    """更新特殊规则"""
    try:
        return await SpecialRuleService.update_rule(db, rule_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

async def _validate_special_rule(
    db: AsyncSession,
    staff_id: int,
    rule_type: str,
    new_params: dict,
    exclude_rule_id: int | None = None,
) -> str | None:
    """
    校验特殊规则与已有规则的冲突。
    返回 None 表示通过，返回字符串表示错误信息。
    """
    # 查询该人员已有的所有规则
    query = select(SchSpecialRule).where(SchSpecialRule.staff_id == staff_id)
    if exclude_rule_id:
        query = query.where(SchSpecialRule.id != exclude_rule_id)

    result = await db.execute(query)
    existing_rules = result.scalars().all()

    rule_type_labels = {
        "exclude_shift": "不排某班次",
        "include_shift": "仅排某班次",
        "exclude_post": "不排某岗位",
        "must_pair": "必须搭配某人",
        "exclude_date": "特定日期不排班",
        "exclude_weekday": "特定星期不排某班",
    }

    for existing in existing_rules:
        e_params = existing.params or {}

        # 1. 完全重复：同类型 + 同参数
        if existing.rule_type == rule_type:
            if json.dumps(e_params, sort_keys=True) == json.dumps(new_params, sort_keys=True):
                label = rule_type_labels.get(rule_type, rule_type)
                return f"已存在相同的「{label}」规则，请勿重复添加"

        # 2. exclude_shift 与 include_shift 互斥冲突
        if rule_type == "exclude_shift" and existing.rule_type == "include_shift":
            excluded = set(new_params.get("exclude_shift_ids", []))
            included = set(e_params.get("include_shift_ids", []))
            overlap = excluded & included
            if overlap:
                return f"排除的班次ID {sorted(overlap)} 与已有的「仅排某班次」规则冲突：这些班次是唯一允许排班的，不能排除"
            # 排除后无可用班次
            remaining = included - excluded
            if remaining == set():
                return "排除这些班次后，已有的「仅排某班次」规则中已无可用班次，会导致该人员无法排班"

        if rule_type == "include_shift" and existing.rule_type == "exclude_shift":
            included = set(new_params.get("include_shift_ids", []))
            excluded = set(e_params.get("exclude_shift_ids", []))
            overlap = included & excluded
            if overlap:
                return f"仅排的班次ID {sorted(overlap)} 与已有的「排除某班次」规则冲突：这些班次已被排除，不能作为仅排班次"
            remaining = included - excluded
            if remaining == set():
                return "选择的班次全部被已有的「排除某班次」规则排除，会导致该人员无法排班"

        # 3. exclude_weekday 与 exclude_shift 重叠提示
        if rule_type == "exclude_weekday" and existing.rule_type == "exclude_shift":
            weekday_shifts = set(new_params.get("exclude_shift_ids", []))
            full_excluded = set(e_params.get("exclude_shift_ids", []))
            overlap = weekday_shifts & full_excluded
            if overlap:
                return f"班次ID {sorted(overlap)} 已被「排除某班次」规则完全排除，无需再设置星期排除"

        if rule_type == "exclude_shift" and existing.rule_type == "exclude_weekday":
            full_excluded = set(new_params.get("exclude_shift_ids", []))
            weekday_shifts = set(e_params.get("exclude_shift_ids", []))
            # 如果排除的班次覆盖了星期排除中的所有班次，则星期排除变得冗余
            if weekday_shifts.issubset(full_excluded):
                return "当前排除的班次已包含「排除星期」规则中的全部班次，星期排除规则将失效"

        # 4. must_pair 搭配人员不能是自己
        if rule_type == "must_pair":
            pair_ids = new_params.get("must_pair_staff_ids", [])
            if staff_id in pair_ids:
                return "不能将自己设为搭配人员"

    return None

@router.delete("/{rule_id}")
async def delete_special_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("constraint", "delete")),
):
    """删除特殊规则"""
    try:
        await SpecialRuleService.delete_rule(db, rule_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
