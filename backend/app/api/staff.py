from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models import OrgStaff, OrgOrganization, SysUser, SysRole, SysUserRole
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse, StaffListResponse, StaffAccountUpdate
from app.api.deps import get_current_user, require_permissions, require_roles
from app.utils.security import hash_password
from pydantic import BaseModel as _BaseModel


class _StaffIdsBody(_BaseModel):
    staff_ids: list[int]

router = APIRouter(prefix="/staffs", tags=["人员管理"])


@router.get("", response_model=StaffListResponse, summary="获取人员列表")
async def get_staff_list(
    org_id: Optional[int] = Query(None, description="组织ID筛选"),
    status: Optional[int] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="姓名/工号搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "read")),
):
    """获取人员列表，支持筛选和分页"""
    query = select(OrgStaff)
    count_query = select(func.count()).select_from(OrgStaff)

    if org_id is not None:
        query = query.where(OrgStaff.org_id == org_id)
        count_query = count_query.where(OrgStaff.org_id == org_id)
    if status is not None:
        query = query.where(OrgStaff.status == status)
        count_query = count_query.where(OrgStaff.status == status)
    if keyword:
        keyword_filter = OrgStaff.name.contains(keyword) | OrgStaff.employee_no.contains(keyword)
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(OrgStaff.employee_no).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    staffs = result.scalars().all()

    items = await _serialize_staff_list(db, staffs)

    return StaffListResponse(total=total, items=items)

@router.post("/reset-password-by-user/{user_id}", summary="通过用户ID重置密码（admin专用）")
async def reset_password_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles('admin')),
):
    """通过用户ID重置密码（admin 等无 staff_id 的账号专用）"""
    DEFAULT_PWD = "admin123"

    user = (await db.execute(
        select(SysUser).where(SysUser.id == user_id)
    )).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password(DEFAULT_PWD)
    user.must_change_password = True
    await db.flush()

    return {
        "message": f"{user.username} 密码已重置为 {DEFAULT_PWD}",
        "default_password": DEFAULT_PWD,
    }

@router.post("/reset-passwords", summary="批量重置密码为默认密码")
async def batch_reset_passwords(
    data: _StaffIdsBody,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """批量将指定人员的账号密码重置为默认密码（123456），admin 不可批量操作"""
    staff_ids = data.staff_ids
    if not staff_ids:
        raise HTTPException(status_code=400, detail="请选择要重置的人员")

    DEFAULT_PWD = "123456"
    default_password_hash = hash_password(DEFAULT_PWD)

    results = []
    for sid in staff_ids:
        staff = (await db.execute(
            select(OrgStaff).where(OrgStaff.id == sid)
        )).scalars().first()
        if not staff:
            results.append({"staff_id": sid, "success": False, "message": "人员不存在"})
            continue

        user = (await db.execute(
            select(SysUser).where(SysUser.staff_id == sid)
        )).scalars().first()
        if not user:
            results.append({"staff_id": sid, "success": False, "message": f"{staff.name} 暂无登录账号"})
            continue

        if user.username == "admin":
            results.append({"staff_id": sid, "success": False, "message": "admin 账号不可批量重置，请单独操作"})
            continue

        user.password_hash = default_password_hash
        user.must_change_password = True
        results.append({
            "staff_id": sid,
            "staff_name": staff.name,
            "success": True,
            "message": f"{staff.name} 密码已重置为 {DEFAULT_PWD}",
        })

    await db.flush()

    success_count = sum(1 for r in results if r["success"])
    return {
        "message": f"已重置 {success_count} 个账号",
        "default_password": DEFAULT_PWD,
        "results": results,
    }


@router.post("/{staff_id}/reset-password", summary="单个重置密码")
async def single_reset_password(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """单个重置密码为默认密码（支持 admin）"""
    staff = (await db.execute(
        select(OrgStaff).where(OrgStaff.id == staff_id)
    )).scalars().first()

    user = None
    if staff:
        user = (await db.execute(
            select(SysUser).where(SysUser.staff_id == staff_id)
        )).scalars().first()

    # 也支持 admin（admin 可能没有 staff 记录，特殊处理）
    if not user:
        # 尝试直接按 staff_id 查
        raise HTTPException(status_code=404, detail="该人员暂无登录账号")

    DEFAULT_PWD = "123456"
    user.password_hash = hash_password(DEFAULT_PWD)
    user.must_change_password = True
    await db.flush()

    display_name = staff.name if staff else user.username
    return {
        "message": f"{display_name} 密码已重置为 {DEFAULT_PWD}",
        "default_password": DEFAULT_PWD,
    }

@router.post("/migrate-accounts", summary="为历史人员批量创建账号")
async def migrate_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "create")),
):
    """为没有登录账号的历史人员批量创建账号（用户名=工号，密码=123456）"""
    result = await db.execute(text("""
        SELECT s.id, s.employee_no, s.name
        FROM org_staff s
        LEFT JOIN sys_user u ON u.staff_id = s.id
        WHERE u.id IS NULL AND s.status = 1
    """))
    rows = result.fetchall()

    if not rows:
        return {"message": "所有人员均已有账号，无需处理", "created": 0}

    member_role = (await db.execute(
        select(SysRole).where(SysRole.code == "member")
    )).scalars().first()

    default_password = hash_password("123456")
    created = 0
    for staff_id, employee_no, name in rows:
        exists = await db.execute(select(SysUser).where(SysUser.username == employee_no))
        if exists.scalar_one_or_none():
            continue

        user = SysUser(
            username=employee_no,
            password_hash=default_password,
            staff_id=staff_id,
            status=1,
            must_change_password=True,
        )
        db.add(user)
        await db.flush()

        if member_role:
            db.add(SysUserRole(user_id=user.id, role_id=member_role.id))
        created += 1

    if created > 0:
        await db.flush()

    return {"message": f"已为 {created} 位人员创建账号（用户名=工号，密码=123456）", "created": created}

@router.get("/system-accounts", summary="获取系统账号列表（admin等无人员关联的账号）")
async def get_system_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles('admin')),
):
    """获取未关联人员的系统账号（如 admin）"""
    from app.models.audit_log import SysAuditLog

    # 查找没有 staff_id 的用户
    result = await db.execute(
        select(SysUser).where(SysUser.staff_id.is_(None))
    )
    users = result.scalars().all()

    # 角色映射
    all_roles = (await db.execute(select(SysRole))).scalars().all()
    role_map = {r.id: r.name for r in all_roles}

    user_ids = [u.id for u in users]
    urs = (await db.execute(
        select(SysUserRole).where(SysUserRole.user_id.in_(user_ids))
    )).scalars().all() if user_ids else []
    user_roles_map: dict[int, list[str]] = {}
    for ur in urs:
        user_roles_map.setdefault(ur.user_id, []).append(role_map.get(ur.role_id, ""))

    items = []
    for u in users:
        items.append({
            "id": None,
            "name": u.username,
            "employee_no": u.username,
            "phone": None,
            "org_id": None,
            "org_name": "系统账号",
            "status": u.status,
            "tags": [],
            "available_posts": [],
            "has_account": True,
            "account_username": u.username,
            "account_status": u.status,
            "account_roles": user_roles_map.get(u.id, []),
            "is_system_account": True,
            "user_id": u.id,
        })

    return {"items": items, "total": len(items)}

# ==================== 选项数据（供排班等页面下拉使用，只需登录权限） ====================

@router.get("/options", summary="获取人员选项列表")
async def get_staff_options(
    org_id: Optional[int] = Query(None, description="组织ID筛选"),
    keyword: Optional[str] = Query(None, description="姓名关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取在岗人员选项（仅返回下拉所需字段，无需 staff.read 权限）"""
    stmt = select(OrgStaff).where(OrgStaff.status == 1)
    if org_id is not None:
        stmt = stmt.where(OrgStaff.org_id == org_id)
    if keyword:
        stmt = stmt.where(OrgStaff.name.ilike(f"%{keyword}%"))
    stmt = stmt.order_by(OrgStaff.employee_no).limit(200)
    result = await db.execute(stmt)
    staffs = result.scalars().all()

    # 批量查组织名称
    org_ids = list({s.org_id for s in staffs})
    org_map: dict[int, str] = {}
    if org_ids:
        orgs = (await db.execute(
            select(OrgOrganization.id, OrgOrganization.name)
            .where(OrgOrganization.id.in_(org_ids))
        )).all()
        org_map = {row[0]: row[1] for row in orgs}

    data = [
        {
            "id": s.id,
            "name": s.name,
            "employee_no": s.employee_no,
            "org_id": s.org_id,
            "org_name": org_map.get(s.org_id, ""),
            "tags": s.tags or [],
        }
        for s in staffs
    ]
    return {"code": 200, "data": data, "message": "success"}


@router.get("/next-employee-no", summary="获取下一个工号")
async def get_next_employee_no(
    org_id: int = Query(..., description="组织ID"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "read")),
):
    """根据组织自动生成下一个工号"""
    from app.utils.employee_no import generate_employee_no
    employee_no = await generate_employee_no(db, org_id)
    return {"employee_no": employee_no}


@router.get("/{staff_id}", response_model=StaffResponse, summary="获取人员详情")
async def get_staff_detail(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "read")),
):
    """获取人员详细信息"""
    result = await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    items = await _serialize_staff_list(db, [staff])
    return items[0]


@router.post("", response_model=StaffResponse, status_code=201, summary="创建人员")
async def create_staff(
    data: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "create")),
):
    """创建人员并自动创建登录账号（用户名=工号，密码=123456，角色由标签自动匹配）"""
    from app.utils.employee_no import generate_employee_no

    # 检查组织存在
    org_result = await db.execute(select(OrgOrganization).where(OrgOrganization.id == data.org_id))
    if not org_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="所属组织不存在")

    # 工号：优先使用传入值，否则自动生成
    employee_no = data.employee_no
    if not employee_no:
        employee_no = await generate_employee_no(db, data.org_id)

    # 检查工号唯一
    result = await db.execute(select(OrgStaff).where(OrgStaff.employee_no == employee_no))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"工号 '{employee_no}' 已存在")

    # 如果要创建账号，先检查用户名是否冲突
    if data.create_account:
        user_exists = await db.execute(select(SysUser).where(SysUser.username == employee_no))
        if user_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"登录账号 '{employee_no}' 已存在")

    # 创建人员
    staff = OrgStaff(
        name=data.name,
        employee_no=employee_no,
        phone=data.phone,
        org_id=data.org_id,
        status=1,
        tags=data.tags,
        available_posts=data.available_posts,
    )
    db.add(staff)
    await db.flush()
    await db.refresh(staff)

    # 根据开关决定是否创建登录账号
    if data.create_account:
        user = SysUser(
            username=data.employee_no,
            password_hash=hash_password("123456"),
            staff_id=staff.id,
            status=1,
            must_change_password=data.must_change_password,
        )
        db.add(user)
        await db.flush()

        # 根据角色标签自动匹配系统角色
        role_ids = await _match_tags_to_roles(db, data.tags or [])
        for rid in role_ids:
            db.add(SysUserRole(user_id=user.id, role_id=rid))
        await db.flush()

    items = await _serialize_staff_list(db, [staff])
    return items[0]


@router.put("/{staff_id}", response_model=StaffResponse, summary="更新人员")
async def update_staff(
    staff_id: int,
    data: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """更新人员信息（不影响关联账号）"""
    result = await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    if data.name is not None:
        staff.name = data.name
    if data.employee_no is not None:
        dup_result = await db.execute(
            select(OrgStaff).where(
                OrgStaff.employee_no == data.employee_no,
                OrgStaff.id != staff_id,
            )
        )
        if dup_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="工号已存在")
        staff.employee_no = data.employee_no
    if data.phone is not None:
        staff.phone = data.phone
    if data.org_id is not None:
        org_result = await db.execute(select(OrgOrganization).where(OrgOrganization.id == data.org_id))
        if not org_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="所属组织不存在")
        staff.org_id = data.org_id
    if data.status is not None:
        staff.status = data.status
    if data.tags is not None:
        staff.tags = data.tags
    if data.available_posts is not None:
        staff.available_posts = data.available_posts

    # 如果标签有变更，自动同步系统角色
    if data.tags is not None:
        user = (await db.execute(select(SysUser).where(SysUser.staff_id == staff_id))).scalars().first()
        if user:
            role_ids = await _match_tags_to_roles(db, data.tags)
            # 清除旧角色
            old_urs = (await db.execute(
                select(SysUserRole).where(SysUserRole.user_id == user.id)
            )).scalars().all()
            for ur in old_urs:
                await db.delete(ur)
            # 写入新角色
            for rid in role_ids:
                db.add(SysUserRole(user_id=user.id, role_id=rid))

    await db.flush()
    await db.refresh(staff)

    items = await _serialize_staff_list(db, [staff])
    return items[0]


@router.put("/{staff_id}/account", response_model=StaffResponse, summary="管理关联账号")
async def update_staff_account(
    staff_id: int,
    data: StaffAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """管理人员关联的登录账号（启用/禁用、重置密码、重新分配角色）"""
    staff = (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    user = (await db.execute(select(SysUser).where(SysUser.staff_id == staff_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="该人员暂无登录账号")

    if data.account_status is not None:
        user.status = data.account_status

    if data.reset_password:
        user.password_hash = hash_password(data.reset_password)
        user.must_change_password = True

    if data.role_ids is not None:
        # 清除旧角色
        old_urs = (await db.execute(
            select(SysUserRole).where(SysUserRole.user_id == user.id)
        )).scalars().all()
        for ur in old_urs:
            await db.delete(ur)
        # 写入新角色
        for rid in data.role_ids:
            role = (await db.execute(select(SysRole).where(SysRole.id == rid))).scalars().first()
            if role:
                db.add(SysUserRole(user_id=user.id, role_id=rid))

    await db.flush()

    items = await _serialize_staff_list(db, [staff])
    return items[0]

@router.put("/{staff_id}/sync-roles", response_model=StaffResponse, summary="同步标签到系统角色")
async def sync_staff_roles(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """根据人员的角色标签，自动同步更新关联账号的系统角色"""
    staff = (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    user = (await db.execute(select(SysUser).where(SysUser.staff_id == staff_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="该人员暂无登录账号")

    # 根据标签匹配角色
    role_ids = await _match_tags_to_roles(db, staff.tags or [])

    # 清除旧角色
    old_urs = (await db.execute(
        select(SysUserRole).where(SysUserRole.user_id == user.id)
    )).scalars().all()
    for ur in old_urs:
        await db.delete(ur)

    # 写入新角色
    for rid in role_ids:
        db.add(SysUserRole(user_id=user.id, role_id=rid))
    await db.flush()

    items = await _serialize_staff_list(db, [staff])
    return items[0]


@router.post("/{staff_id}/account", response_model=StaffResponse, status_code=201, summary="为已有人员创建账号")
async def create_account_for_staff(
    staff_id: int,
    password: str = Query(..., min_length=6, description="初始密码"),
    must_change_password: bool = Query(True, description="首次登录是否需要改密"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "update")),
):
    """为没有账号的人员创建登录账号（用户名=工号）"""
    staff = (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    existing = (await db.execute(select(SysUser).where(SysUser.staff_id == staff_id))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="该人员已有登录账号")

    username = staff.employee_no
    user_exists = await db.execute(select(SysUser).where(SysUser.username == username))
    if user_exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"登录账号 '{username}' 已被占用")

    user = SysUser(
        username=username,
        password_hash=hash_password(password),
        staff_id=staff.id,
        status=1,
        must_change_password=must_change_password,
    )
    db.add(user)
    await db.flush()

    # 根据人员标签自动匹配系统角色
    role_ids = await _match_tags_to_roles(db, staff.tags or [])
    for rid in role_ids:
        db.add(SysUserRole(user_id=user.id, role_id=rid))
    await db.flush()

    items = await _serialize_staff_list(db, [staff])
    return items[0]


@router.delete("/{staff_id}", summary="删除人员")
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("staff", "delete")),
):
    """删除人员（同步删除关联账号）"""
    staff = (await db.execute(select(OrgStaff).where(OrgStaff.id == staff_id))).scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="人员不存在")

    # 同步删除关联账号
    user = (await db.execute(select(SysUser).where(SysUser.staff_id == staff_id))).scalars().first()
    if user:
        if user.username == "admin":
            raise HTTPException(status_code=400, detail="admin 账号关联的人员不可删除")
        # 清除角色关联
        urs = (await db.execute(select(SysUserRole).where(SysUserRole.user_id == user.id))).scalars().all()
        for ur in urs:
            await db.delete(ur)
        await db.delete(user)

    await db.delete(staff)
    return {"message": "删除成功"}


# ========== 私有辅助函数 ==========
async def _match_tags_to_roles(db: AsyncSession, tags: list[str]) -> list[int]:
    """根据人员标签自动匹配系统角色ID"""
    if not tags:
        # 无标签，分配默认 member 角色
        member = (await db.execute(select(SysRole).where(SysRole.code == "member"))).scalars().first()
        return [member.id] if member else []

    all_roles = (await db.execute(select(SysRole))).scalars().all()
    # 按角色名称匹配标签
    role_name_map = {r.name: r.id for r in all_roles}

    matched_ids = []
    for tag in tags:
        if tag in role_name_map:
            matched_ids.append(role_name_map[tag])

    if not matched_ids:
        # 标签未匹配到任何角色，分配默认 member
        member = next((r for r in all_roles if r.code == "member"), None)
        if member:
            matched_ids.append(member.id)

    return matched_ids

async def _serialize_staff_list(db: AsyncSession, staffs: list) -> list[StaffResponse]:
    """序列化人员列表（含账号信息）"""
    if not staffs:
        return []

    staff_ids = [s.id for s in staffs]
    users = (await db.execute(
        select(SysUser).where(SysUser.staff_id.in_(staff_ids))
    )).scalars().all()

    # 用户 → 人员映射
    staff_user_map: dict[int, SysUser] = {}
    user_ids = [u.id for u in users]
    for u in users:
        staff_user_map[u.staff_id] = u

    # 角色映射
    all_roles = (await db.execute(select(SysRole))).scalars().all()
    role_map = {r.id: r.name for r in all_roles}

    urs = (await db.execute(
        select(SysUserRole).where(SysUserRole.user_id.in_(user_ids))
    )).scalars().all() if user_ids else []
    user_roles_map: dict[int, list[str]] = {}
    for ur in urs:
        user_roles_map.setdefault(ur.user_id, []).append(role_map.get(ur.role_id, ""))

    items = []
    for staff in staffs:
        item = StaffResponse.model_validate(staff)
        if staff.organization:
            item.org_name = staff.organization.name

        user = staff_user_map.get(staff.id)
        if user:
            item.has_account = True
            item.account_username = user.username
            item.account_status = user.status
            item.account_roles = user_roles_map.get(user.id, [])

        items.append(item)

    return items
