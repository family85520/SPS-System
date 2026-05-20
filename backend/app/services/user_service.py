"""用户账号管理服务（全异步）"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SysUser, SysRole, SysUserRole, OrgStaff
from app.utils.security import hash_password


class UserService:
    """用户账号管理服务"""

    @staticmethod
    async def get_list(
        db: AsyncSession,
        *,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        role_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取用户列表"""
        query = select(SysUser)

        if status is not None:
            query = query.where(SysUser.status == status)
        if keyword:
            query = query.where(SysUser.username.ilike(f"%{keyword}%"))

        if role_id:
            ur_sub = select(SysUserRole.user_id).where(SysUserRole.role_id == role_id)
            query = query.where(SysUser.id.in_(ur_sub))

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0

        query = query.order_by(SysUser.id).offset((page - 1) * page_size).limit(page_size)
        users = list((await db.execute(query)).scalars().all())

        items = await _serialize_users(db, users)
        return {"items": items, "total": total}

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> dict:
        """获取用户详情"""
        user = (await db.execute(
            select(SysUser).where(SysUser.id == user_id)
        )).scalars().first()
        if not user:
            raise ValueError("用户不存在")
        items = await _serialize_users(db, [user])
        return items[0] if items else {}

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> dict:
        """创建用户"""
        username = data["username"]
        existing = (await db.execute(
            select(SysUser).where(SysUser.username == username)
        )).scalars().first()
        if existing:
            raise ValueError(f"用户名 '{username}' 已存在")

        staff_id = data.get("staff_id")
        create_staff = data.get("create_staff", False)

        # 模式一：关联已有人员
        if staff_id and not create_staff:
            staff = (await db.execute(
                select(OrgStaff).where(OrgStaff.id == staff_id)
            )).scalars().first()
            if not staff:
                raise ValueError("关联人员不存在")
            bound = (await db.execute(
                select(SysUser).where(SysUser.staff_id == staff_id)
            )).scalars().first()
            if bound:
                raise ValueError(f"该人员已关联用户 '{bound.username}'，不可重复绑定")

        # 模式二：同步创建人员
        if create_staff:
            staff_name = data.get("staff_name")
            employee_no = data.get("employee_no")
            org_id = data.get("org_id")
            if not staff_name or not employee_no or not org_id:
                raise ValueError("同步创建人员时，姓名、工号、所属组织为必填项")

            # 工号唯一检查
            dup_staff = (await db.execute(
                select(OrgStaff).where(OrgStaff.employee_no == employee_no)
            )).scalars().first()
            if dup_staff:
                raise ValueError(f"工号 '{employee_no}' 已存在")

            new_staff = OrgStaff(
                name=staff_name,
                employee_no=employee_no,
                phone=data.get("phone"),
                org_id=org_id,
                status=1,
                tags=data.get("staff_tags"),
            )
            db.add(new_staff)
            await db.flush()
            await db.refresh(new_staff)
            staff_id = new_staff.id

        user = SysUser(
            username=username,
            password_hash=hash_password(data["password"]),
            staff_id=staff_id,
            status=data.get("status", 1),
            must_change_password=data.get("must_change_password", True),
        )
        db.add(user)
        await db.flush()

        role_ids = data.get("role_ids", [])
        if role_ids:
            await _assign_roles(db, user.id, role_ids)

        await db.refresh(user)
        items = await _serialize_users(db, [user])
        return items[0] if items else {}

    @staticmethod
    async def update(db: AsyncSession, user_id: int, data: dict) -> dict:
        """更新用户"""
        user = (await db.execute(
            select(SysUser).where(SysUser.id == user_id)
        )).scalars().first()
        if not user:
            raise ValueError("用户不存在")

        if "staff_id" in data and data["staff_id"] is not None:
            staff_id = data["staff_id"]
            staff = (await db.execute(
                select(OrgStaff).where(OrgStaff.id == staff_id)
            )).scalars().first()
            if not staff:
                raise ValueError("关联人员不存在")
            bound = (await db.execute(
                select(SysUser).where(SysUser.staff_id == staff_id, SysUser.id != user_id)
            )).scalars().first()
            if bound:
                raise ValueError(f"该人员已关联用户 '{bound.username}'，不可重复绑定")
            user.staff_id = staff_id

        if "status" in data and data["status"] is not None:
            user.status = data["status"]

        if "role_ids" in data and data["role_ids"] is not None:
            await _assign_roles(db, user.id, data["role_ids"])

        await db.flush()
        await db.refresh(user)
        items = await _serialize_users(db, [user])
        return items[0] if items else {}

    @staticmethod
    async def reset_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
        """重置密码"""
        user = (await db.execute(
            select(SysUser).where(SysUser.id == user_id)
        )).scalars().first()
        if not user:
            raise ValueError("用户不存在")

        user.password_hash = hash_password(new_password)
        await db.flush()
        return True

    @staticmethod
    async def delete(db: AsyncSession, user_id: int) -> bool:
        """删除用户"""
        user = (await db.execute(
            select(SysUser).where(SysUser.id == user_id)
        )).scalars().first()
        if not user:
            raise ValueError("用户不存在")
        if user.username == "admin":
            raise ValueError("admin 账号不可删除")

        await _remove_all_roles(db, user_id)
        await db.delete(user)
        await db.flush()
        return True


# ========== 私有辅助函数 ==========

async def _assign_roles(db: AsyncSession, user_id: int, role_ids: list[int]):
    """分配角色（先清空再写入）"""
    await _remove_all_roles(db, user_id)
    for rid in role_ids:
        role = (await db.execute(
            select(SysRole).where(SysRole.id == rid)
        )).scalars().first()
        if role:
            db.add(SysUserRole(user_id=user_id, role_id=rid))
    await db.flush()


async def _remove_all_roles(db: AsyncSession, user_id: int):
    """清除用户所有角色"""
    urs = (await db.execute(
        select(SysUserRole).where(SysUserRole.user_id == user_id)
    )).scalars().all()
    for ur in urs:
        await db.delete(ur)
    await db.flush()


async def _serialize_users(db: AsyncSession, users: list[SysUser]) -> list[dict]:
    """序列化用户列表"""
    if not users:
        return []

    user_ids = [u.id for u in users]
    staff_ids = [u.staff_id for u in users if u.staff_id]

    # 人员姓名映射
    staff_map: dict[int, str] = {}
    if staff_ids:
        rows = (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(staff_ids))
        )).all()
        staff_map = {row[0]: row[1] for row in rows}

    # 角色映射
    all_roles = (await db.execute(select(SysRole))).scalars().all()
    role_map = {r.id: r.name for r in all_roles}

    # 用户角色关联
    urs = (await db.execute(
        select(SysUserRole).where(SysUserRole.user_id.in_(user_ids))
    )).scalars().all()
    user_roles_map: dict[int, list[dict]] = {}
    for ur in urs:
        user_roles_map.setdefault(ur.user_id, []).append({
            "id": ur.role_id,
            "name": role_map.get(ur.role_id, ""),
        })

    # 最后登录时间（从 audit_log 查）
    from app.models.audit_log import SysAuditLog
    last_login_map: dict[int, datetime] = {}
    for uid in user_ids:
        row = (await db.execute(
            select(SysAuditLog.created_at)
            .where(SysAuditLog.user_id == uid, SysAuditLog.action == "login")
            .order_by(SysAuditLog.created_at.desc())
            .limit(1)
        )).scalars().first()
        if row:
            last_login_map[uid] = row

    items = []
    for u in users:
        ur_list = user_roles_map.get(u.id, [])
        items.append({
            "id": u.id,
            "username": u.username,
            "staff_id": u.staff_id,
            "staff_name": staff_map.get(u.staff_id) if u.staff_id else None,
            "status": u.status,
            "roles": [r["name"] for r in ur_list],
            "role_ids": [r["id"] for r in ur_list],
            "created_at": u.created_at,
            "updated_at": u.updated_at,
            "last_login_at": last_login_map.get(u.id),
        })

    return items
