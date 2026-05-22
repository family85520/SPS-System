"""消息系统 API 路由（异步）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models import SysUser
from app.schemas.message import BroadcastRequest, AnnouncementCreate, AnnouncementUpdate
from app.services.message_service import MessageService, AnnouncementService

router = APIRouter(tags=["消息管理"])


# ==================== 消息 API ====================

@router.get("/messages", summary="获取消息列表")
async def get_messages(
    msg_type: str | None = Query(None, description="消息类型筛选"),
    is_read: bool | None = Query(None, description="已读状态筛选"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "read")),
):
    result = await MessageService.get_messages(
        db, receiver_id=current_user.id, msg_type=msg_type,
        is_read=is_read, keyword=keyword, page=page, size=size,
    )
    return {"code": 200, "data": result, "message": "success"}


@router.get("/messages/unread-count", summary="获取未读消息数量")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "read")),
):
    result = await MessageService.get_unread_count(db, receiver_id=current_user.id)
    return {"code": 200, "data": result, "message": "success"}


@router.put("/messages/{message_id}/read", summary="标记单条消息为已读")
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "read")),
):
    success = await MessageService.mark_as_read(db, message_id=message_id, receiver_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="消息不存在或无权操作")
    return {"code": 200, "data": None, "message": "标记成功"}


@router.put("/messages/read-all", summary="全部标记已读")
async def mark_all_messages_read(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "read")),
):
    count = await MessageService.mark_all_as_read(db, receiver_id=current_user.id)
    return {"code": 200, "data": {"count": count}, "message": f"已标记 {count} 条消息为已读"}


@router.post("/messages/broadcast", summary="广播消息（管理员）")
async def broadcast_message(
    data: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "create")),
):
    messages = await MessageService.broadcast_message(
        db, title=data.title, content=data.content, msg_type=data.msg_type,
        sender_id=current_user.id, target_scope=data.target_scope,
        target_ids=data.target_ids, relation_type=data.relation_type,
        relation_id=data.relation_id,
    )
    return {"code": 200, "data": {"sent_count": len(messages)}, "message": f"成功发送 {len(messages)} 条消息"}


# ==================== 公告 API ====================

@router.get("/announcements", summary="获取公告列表")
async def get_announcements(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None, description="筛选有效状态，不传则显示全部未删除的"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "read")),
):
    result = await AnnouncementService.get_announcements(db, page=page, size=size, is_active=is_active)
    return {"code": 200, "data": result, "message": "success"}


@router.post("/announcements", summary="发布公告")
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "create")),
):
    ann = await AnnouncementService.create_announcement(
        db, title=data.title, content=data.content, publisher_id=current_user.id,
        target_scope=data.target_scope, target_ids=data.target_ids,
    )
    return {"code": 200, "data": {"id": ann.id, "title": ann.title}, "message": "公告发布成功"}


@router.put("/announcements/{ann_id}", summary="编辑公告")
async def update_announcement(
    ann_id: int,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "create")),
):
    result = await AnnouncementService.update_announcement(
        db, ann_id=ann_id, data=data.model_dump(exclude_unset=True),
    )
    if not result:
        raise HTTPException(status_code=404, detail="公告不存在")
    return {"code": 200, "data": result, "message": "更新成功"}


@router.post("/announcements/{ann_id}/withdraw", summary="撤回公告")
async def withdraw_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "delete")),
):
    success = await AnnouncementService.withdraw_announcement(db, ann_id=ann_id)
    if not success:
        raise HTTPException(status_code=400, detail="公告不存在或已撤回")
    return {"code": 200, "data": None, "message": "公告已撤回"}


@router.delete("/announcements/{ann_id}", summary="永久隐藏公告（仅已撤回可操作）")
async def delete_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("message", "delete")),
):
    success = await AnnouncementService.delete_announcement(db, ann_id=ann_id)
    if not success:
        raise HTTPException(status_code=400, detail="公告不存在或未撤回")
    return {"code": 200, "data": None, "message": "公告已永久隐藏"}


# ==================== 选项数据（组织/角色/人员） ====================

@router.get("/options/organizations", summary="获取组织选项列表")
async def get_org_options(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.models import OrgOrganization
    orgs = (await db.execute(
        select(OrgOrganization)
        .where(OrgOrganization.status == 1)
        .order_by(OrgOrganization.sort_order)
    )).scalars().all()
    data = [{"id": o.id, "name": o.name} for o in orgs]
    return {"code": 200, "data": data, "message": "success"}


@router.get("/options/roles", summary="获取角色选项列表")
async def get_role_options(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.models import SysRole
    roles = (await db.execute(
        select(SysRole).order_by(SysRole.id)
    )).scalars().all()
    data = [{"id": r.id, "name": r.name, "code": r.code} for r in roles]
    return {"code": 200, "data": data, "message": "success"}


@router.get("/options/staffs", summary="搜索人员选项列表")
async def search_staff_options(
    keyword: str = Query(..., min_length=1, description="姓名关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.models import OrgStaff, OrgOrganization
    pattern = f"%{keyword}%"
    staffs = (await db.execute(
        select(OrgStaff)
        .where(OrgStaff.name.ilike(pattern), OrgStaff.status == 1)
        .limit(20)
    )).scalars().all()

    org_ids = list({s.org_id for s in staffs})
    org_map: dict[int, str] = {}
    if org_ids:
        orgs = (await db.execute(
            select(OrgOrganization.id, OrgOrganization.name)
            .where(OrgOrganization.id.in_(org_ids))
        )).all()
        org_map = {row[0]: row[1] for row in orgs}

    data = [
        {"id": s.id, "name": s.name, "org_name": org_map.get(s.org_id, "")}
        for s in staffs
    ]
    return {"code": 200, "data": data, "message": "success"}
