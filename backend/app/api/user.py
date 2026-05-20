"""用户账号管理 API 路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models import SysUser
from app.schemas.user import (
    UserCreate, UserUpdate, ResetPasswordRequest,
    UserResponse, UserListResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户账号管理"])


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def list_users(
    keyword: str | None = Query(None, description="用户名搜索"),
    status: int | None = Query(None, description="状态筛选"),
    role_id: int | None = Query(None, description="角色筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "read")),
):
    result = await UserService.get_list(
        db, keyword=keyword, status=status, role_id=role_id,
        page=page, page_size=page_size,
    )
    return UserListResponse(items=result["items"], total=result["total"])


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "read")),
):
    try:
        return await UserService.get_by_id(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=UserResponse, status_code=201, summary="创建用户")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "create")),
):
    try:
        return await UserService.create(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "update")),
):
    try:
        return await UserService.update(db, user_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}/password", summary="重置密码")
async def reset_password(
    user_id: int,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "update")),
):
    try:
        await UserService.reset_password(db, user_id, data.new_password)
        return {"message": "密码重置成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("user", "delete")),
):
    try:
        await UserService.delete(db, user_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
