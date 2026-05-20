from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.auth import get_current_user
from app.models import SysUser
from app.schemas.constraint import (
    ConstraintCreate,
    ConstraintUpdate,
    ConstraintResponse,
    BatchPriorityRequest,
)
from app.services.constraint_service import ConstraintService

router = APIRouter(prefix="/constraints", tags=["约束规则管理"])


@router.get("", response_model=list[ConstraintResponse])
async def list_constraints(
    enabled: Optional[bool] = Query(None, description="是否启用筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取约束规则列表"""
    return await ConstraintService.list_constraints(db, enabled=enabled)


@router.get("/{constraint_id}", response_model=ConstraintResponse)
async def get_constraint(
    constraint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取单个约束规则详情"""
    constraint = await ConstraintService.get_constraint(db, constraint_id)
    if not constraint:
        raise HTTPException(status_code=404, detail="约束规则不存在")
    return constraint


@router.post("", response_model=ConstraintResponse, status_code=201)
async def create_constraint(
    data: ConstraintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """创建约束规则"""
    try:
        return await ConstraintService.create_constraint(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{constraint_id}", response_model=ConstraintResponse)
async def update_constraint(
    constraint_id: int,
    data: ConstraintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """更新约束规则"""
    try:
        return await ConstraintService.update_constraint(db, constraint_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{constraint_id}")
async def delete_constraint(
    constraint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """删除约束规则"""
    try:
        await ConstraintService.delete_constraint(db, constraint_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/{constraint_id}/toggle", response_model=ConstraintResponse)
async def toggle_constraint(
    constraint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """启用/禁用约束规则"""
    try:
        return await ConstraintService.toggle_constraint(db, constraint_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.put("/batch/priority")
async def batch_update_priority(
    data: BatchPriorityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """批量更新优先级"""
    try:
        await ConstraintService.batch_update_priority(db, data)
        return {"message": "优先级更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
