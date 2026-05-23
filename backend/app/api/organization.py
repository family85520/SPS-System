from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import OrgOrganization, OrgStaff
from app.models.schedule import SchSchedule
from app.schemas.organization import OrgCreate, OrgUpdate, OrgResponse, OrgTreeResponse
from app.api.deps import get_current_user, require_permissions
from app.models import SysUser
from app.utils.employee_no import generate_org_code

router = APIRouter(prefix="/organizations", tags=["组织架构管理"])


async def _get_org_with_children(db: AsyncSession, org_id: int) -> OrgOrganization:
    """获取组织及其子组织"""
    result = await db.execute(select(OrgOrganization).where(OrgOrganization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    return org


def _build_tree(orgs: List[OrgOrganization], parent_id: Optional[int] = None) -> List[dict]:
    """递归构建组织树"""
    tree = []
    for org in orgs:
        if org.parent_id == parent_id:
            node = {
                "id": org.id,
                "name": org.name,
                "code": getattr(org, "code", None),
                "parent_id": org.parent_id,
                "level": org.level,
                "sort_order": org.sort_order,
                "status": org.status,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
                "children": _build_tree(orgs, org.id),
            }
            tree.append(node)
    tree.sort(key=lambda x: x["sort_order"])
    return tree


@router.get("/tree", summary="获取组织架构树")
async def get_org_tree(
    include_disabled: bool = Query(False, description="是否包含停用的组织"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("organization", "read")),
):
    """获取完整的组织架构树"""
    query = select(OrgOrganization).options(selectinload(OrgOrganization.children))
    if not include_disabled:
        query = query.where(OrgOrganization.status == 1)
    query = query.order_by(OrgOrganization.sort_order)

    result = await db.execute(query)
    orgs = result.scalars().all()

    tree = _build_tree(orgs)
    return tree


@router.get("", response_model=List[OrgResponse], summary="获取组织列表")
async def get_org_list(
    parent_id: Optional[int] = Query(None, description="上级组织ID"),
    include_disabled: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("organization", "read")),
):
    """获取组织列表，可按上级组织筛选"""
    query = select(OrgOrganization).options(selectinload(OrgOrganization.children))

    if parent_id is not None:
        query = query.where(OrgOrganization.parent_id == parent_id)
    if not include_disabled:
        query = query.where(OrgOrganization.status == 1)

    query = query.order_by(OrgOrganization.sort_order)
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.post("", response_model=OrgResponse, status_code=201, summary="创建组织")
async def create_org(
    data: OrgCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("organization", "create")),
):
    """创建新的组织"""
    # 计算层级
    level = 1
    if data.parent_id:
        parent = await _get_org_with_children(db, data.parent_id)
        level = parent.level + 1
        if level > 4:
            raise HTTPException(status_code=400, detail="组织层级最多支持4级")

    # 检查同级名称唯一
    query = select(OrgOrganization).where(
        OrgOrganization.parent_id == data.parent_id,
        OrgOrganization.name == data.name,
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="同级组织名称已存在")

    # 部门代码：优先使用传入值，否则自动生成
    code = data.code
    if not code:
        code = await generate_org_code(db, data.name)
    else:
        # 检查手动输入的 code 唯一性
        dup = (await db.execute(
            select(OrgOrganization).where(OrgOrganization.code == code)
        )).scalars().first()
        if dup:
            raise HTTPException(status_code=400, detail=f"部门代码 '{code}' 已存在")

    org = OrgOrganization(
        name=data.name,
        code=code,
        parent_id=data.parent_id,
        level=level,
        sort_order=data.sort_order,
        status=1,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)

    return org


@router.put("/{org_id}", response_model=OrgResponse, summary="更新组织")
async def update_org(
    org_id: int,
    data: OrgUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("organization", "update")),
):
    """更新组织信息"""
    org = await _get_org_with_children(db, org_id)

    if data.name is not None:
        # 检查同级名称唯一
        query = select(OrgOrganization).where(
            OrgOrganization.parent_id == org.parent_id,
            OrgOrganization.name == data.name,
            OrgOrganization.id != org_id,
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="同级组织名称已存在")
        org.name = data.name

    if data.code is not None:
        code = data.code.strip()
        if code:
            dup = (await db.execute(
                select(OrgOrganization).where(
                    OrgOrganization.code == code,
                    OrgOrganization.id != org_id,
                )
            )).scalars().first()
            if dup:
                raise HTTPException(status_code=400, detail=f"部门代码 '{code}' 已存在")
            org.code = code

    if data.sort_order is not None:
        org.sort_order = data.sort_order

    if data.status is not None:
        # 检查是否有人员关联
        if data.status == 0:
            staff_count = await db.execute(
                select(func.count()).select_from(OrgStaff).where(OrgStaff.org_id == org_id)
            )
            if staff_count.scalar() > 0:
                raise HTTPException(status_code=400, detail="该组织下有人员，只能停用不能删除")
        org.status = data.status

    await db.flush()
    await db.refresh(org)

    return org


@router.delete("/{org_id}", summary="删除组织")
async def delete_org(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("organization", "delete")),
):
    """删除组织（仅无人员关联的末级组织可删除）"""
    org = await _get_org_with_children(db, org_id)

    # 检查是否有子组织
    child_count = await db.execute(
        select(func.count()).select_from(OrgOrganization).where(OrgOrganization.parent_id == org_id)
    )
    if child_count.scalar() > 0:
        raise HTTPException(status_code=400, detail="该组织下有子组织，无法删除")

    # 检查是否有人员
    staff_count = await db.execute(
        select(func.count()).select_from(OrgStaff).where(OrgStaff.org_id == org_id)
    )
    if staff_count.scalar() > 0:
        raise HTTPException(status_code=400, detail="该组织下有人员，请先删除组织下的人员再删除组织")

    # 检查是否有排班记录
    schedule_count = await db.execute(
        select(func.count()).select_from(SchSchedule).where(SchSchedule.org_id == org_id)
    )
    if schedule_count.scalar() > 0:
        raise HTTPException(status_code=400, detail="该组织下存在排班记录，无法删除")

    await db.delete(org)
    await db.flush()

    return {"message": "删除成功"}
