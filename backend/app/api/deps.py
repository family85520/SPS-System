from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.utils.security import decode_access_token
from app.models import SysUser, SysRole

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> SysUser:
    """获取当前登录用户"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户信息",
        )

    result = await db.execute(select(SysUser).where(SysUser.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


def require_roles(*role_codes: str):
    """要求用户具有指定角色"""
    async def role_checker(current_user: SysUser = Depends(get_current_user)) -> SysUser:
        user_role_codes = [role.code for role in current_user.roles]

        # 系统管理员拥有所有权限
        if "admin" in user_role_codes:
            return current_user

        # 检查是否有所需角色
        if not any(code in user_role_codes for code in role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一：{', '.join(role_codes)}",
            )

        return current_user

    return role_checker


def require_permissions(resource: str, action: str):
    """要求用户具有指定权限"""
    async def permission_checker(current_user: SysUser = Depends(get_current_user)) -> SysUser:
        # 系统管理员拥有所有权限
        for role in current_user.roles:
            if role.code == "admin":
                return current_user
            if role.permissions:
                if role.permissions.get("all"):
                    return current_user
                resource_perms = role.permissions.get(resource)
                if resource_perms and action in resource_perms:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"没有 {resource}:{action} 权限",
        )

    return permission_checker
