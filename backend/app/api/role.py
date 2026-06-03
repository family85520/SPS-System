from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_roles, require_permissions
from app.models import SysUser
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRoleAssign,
    StaffTagAssign,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["角色权限管理"])


@router.get("/permission-schema", summary="获取权限规格表")
async def get_permission_schema(
    current_user: SysUser = Depends(require_roles("admin")),
):
    """返回每个模块支持的操作列表，前端根据此数据动态渲染权限矩阵"""
    return {
        "modules": [
            {
                "key": "organization",
                "label": "组织管理",
                "actions": ["read", "create", "update", "delete"],
            },
            {
                "key": "staff",
                "label": "人员管理",
                "actions": ["read", "create", "update", "delete"],
            },
            {
                "key": "shift_template",
                "label": "班次模板",
                "actions": ["read", "create", "update", "delete"],
            },
            {
                "key": "constraint",
                "label": "约束规则",
                "actions": ["read", "create", "update", "delete"],
            },
            {
                "key": "schedule",
                "label": "排班管理",
                "actions": ["read", "create", "update", "delete", "publish", "approve"],
            },
            {
                "key": "swap",
                "label": "调班管理",
                "actions": ["read", "create", "approve"],
            },
            {
                "key": "message",
                "label": "消息中心",
                "actions": ["read", "create", "delete"],
            },
            {
                "key": "export",
                "label": "数据导出",
                "actions": ["read"],
            },
        ],
        "actions": [
            {"key": "read", "label": "查看"},
            {"key": "create", "label": "创建"},
            {"key": "update", "label": "编辑"},
            {"key": "delete", "label": "删除"},
            {"key": "publish", "label": "发布"},
            {"key": "approve", "label": "审批"},
        ],
    }


@router.get("/options", summary="获取角色选项列表")
async def get_role_options(
    type: Optional[str] = Query(None, description="筛选类型: role=角色 tag=标识"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取角色选项（登录即可，支持按类型筛选）"""
    from app.models import SysRole
    from typing import Optional as _Optional
    stmt = select(SysRole).order_by(SysRole.id)
    if type in ("role", "tag"):
        stmt = stmt.where(SysRole.role_type == type)
    roles = (await db.execute(stmt)).scalars().all()
    data = [{"id": r.id, "name": r.name, "code": r.code, "role_type": r.role_type} for r in roles]
    return {"code": 200, "data": data, "message": "success"}


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """获取角色列表"""
    return await RoleService.list_roles(db)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """获取角色详情"""
    role = await RoleService.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """创建自定义角色"""
    try:
        dump = data.model_dump()
        # 标识类型强制清空权限
        if dump.get("role_type") == "tag":
            dump["permissions"] = None
        return await RoleService.create_role(db, dump)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """更新角色"""
    try:
        return await RoleService.update_role(db, role_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """删除自定义角色"""
    try:
        await RoleService.delete_role(db, role_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/user/{user_id}", response_model=list[RoleResponse])
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """获取用户的角色列表"""
    try:
        return await RoleService.get_user_roles(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/user/{user_id}")
async def assign_user_roles(
    user_id: int,
    data: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """为用户分配角色"""
    try:
        await RoleService.assign_user_roles(db, user_id, data.role_ids)
        return {"message": "角色分配成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分配失败: {str(e)}")

# ==================== 人员标识管理 ====================

@router.get("/staff/{staff_id}/tags", summary="获取人员的标识列表")
async def get_staff_tags(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "read")),
):
    """获取人员被分配的所有标识"""
    tags = await RoleService.get_staff_tags(db, staff_id)
    # 加载角色详情
    result = []
    for t in tags:
        role = await RoleService.get_role(db, t.role_id)
        if role:
            result.append({
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "role_type": role.role_type,
            })
    return result


@router.post("/staff/{staff_id}/tags", summary="为人员分配标识")
async def assign_staff_tags(
    staff_id: int,
    data: StaffTagAssign,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """为人员分配标识（全量替换）"""
    try:
        await RoleService.assign_staff_tags(db, staff_id, data.role_ids)
        return {"message": "标识分配成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/staff/{staff_id}/tags/{role_id}", summary="移除人员的单个标识")
async def remove_staff_tag(
    staff_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """移除人员的单个标识"""
    try:
        await RoleService.remove_staff_tag(db, staff_id, role_id)
        return {"message": "标识已移除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
