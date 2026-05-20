from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models import SysRole, SysUser, SysUserRole


class RoleService:
    """角色权限服务"""

    @staticmethod
    async def list_roles(db: AsyncSession):
        """获取角色列表"""
        stmt = select(SysRole).order_by(SysRole.id.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_role(db: AsyncSession, role_id: int) -> Optional[SysRole]:
        """获取单个角色"""
        stmt = select(SysRole).where(SysRole.id == role_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_role(db: AsyncSession, data: dict) -> SysRole:
        """创建自定义角色"""
        # 检查 code 是否重复
        dup_stmt = select(SysRole).where(SysRole.code == data["code"])
        dup_result = await db.execute(dup_stmt)
        if dup_result.scalars().first():
            raise ValueError(f"角色编码「{data['code']}」已存在")

        role = SysRole(
            name=data["name"],
            code=data["code"],
            permissions=data.get("permissions"),
            is_system=False,
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, data: dict) -> SysRole:
        """更新角色"""
        role = await RoleService.get_role(db, role_id)
        if not role:
            raise ValueError("角色不存在")

        for field, value in data.items():
            if value is not None:
                setattr(role, field, value)

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int):
        """删除角色"""
        role = await RoleService.get_role(db, role_id)
        if not role:
            raise ValueError("角色不存在")

        if role.is_system:
            raise ValueError("系统内置角色不可删除")

        # 删除关联的用户角色记录
        ur_stmt = select(SysUserRole).where(SysUserRole.role_id == role_id)
        ur_result = await db.execute(ur_stmt)
        for ur in ur_result.scalars().all():
            await db.delete(ur)

        await db.delete(role)
        await db.commit()

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int):
        """获取用户的角色列表"""
        user_stmt = select(SysUser).where(SysUser.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalars().first()
        if not user:
            raise ValueError("用户不存在")
        return user.roles

    @staticmethod
    async def assign_user_roles(db: AsyncSession, user_id: int, role_ids: list[int]):
        """为用户分配角色"""
        # 校验用户存在
        user_stmt = select(SysUser).where(SysUser.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalars().first()
        if not user:
            raise ValueError("用户不存在")

        # 校验所有角色存在
        for rid in role_ids:
            role_stmt = select(SysRole).where(SysRole.id == rid)
            role_result = await db.execute(role_stmt)
            if not role_result.scalars().first():
                raise ValueError(f"角色ID {rid} 不存在")

        # 删除旧关联
        old_stmt = select(SysUserRole).where(SysUserRole.user_id == user_id)
        old_result = await db.execute(old_stmt)
        for ur in old_result.scalars().all():
            await db.delete(ur)

        # 创建新关联
        for rid in role_ids:
            db.add(SysUserRole(user_id=user_id, role_id=rid))

        await db.commit()
