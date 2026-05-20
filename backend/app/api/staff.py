from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models import OrgStaff, OrgOrganization, SysUser, SysRole, SysUserRole
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse, StaffListResponse, StaffAccountUpdate
from app.api.deps import get_current_user, require_permissions
from app.utils.security import hash_password

router = APIRouter(prefix="/staffs", tags=["人员管理"])


@router.get("", response_model=StaffListResponse, summary="获取人员列表")
async def get_staff_list(
    org_id: Optional[int] = Query(None, description="组织ID筛选"),
    status: Optional[int] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="姓名/工号搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
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


@router.post("/migrate-accounts", summary="为历史人员批量创建账号")
async def migrate_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
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


@router.get("/{staff_id}", response_model=StaffResponse, summary="获取人员详情")
async def get_staff_detail(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
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
    # 检查工号唯一
    result = await db.execute(select(OrgStaff).where(OrgStaff.employee_no == data.employee_no))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="工号已存在")

    # 检查组织存在
    org_result = await db.execute(select(OrgOrganization).where(OrgOrganization.id == data.org_id))
    if not org_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="所属组织不存在")

    # 如果要创建账号，先检查用户名是否冲突
    if data.create_account:
        user_exists = await db.execute(select(SysUser).where(SysUser.username == data.employee_no))
        if user_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"登录账号 '{data.employee_no}' 已存在（工号与已有账号重复）")

    # 创建人员
    staff = OrgStaff(
        name=data.name,
        employee_no=data.employee_no,
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
