"""消息系统服务（全异步）"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SysUser, OrgStaff, SysUserRole
from app.models.message import SysMessage, SysAnnouncement
from app.utils.time_helper import to_local_str as _to_local_str


class MessageService:
    """消息服务"""

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        *,
        receiver_id: int,
        msg_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """分页查询消息列表"""
        query = select(SysMessage).where(
            SysMessage.receiver_id == receiver_id,
            SysMessage.deleted_at.is_(None),
            SysMessage.title.notilike("[已删除]%"),
        )

        if msg_type:
            query = query.where(SysMessage.msg_type == msg_type)
        if is_read is not None:
            query = query.where(SysMessage.is_read == is_read)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(
                (SysMessage.title.ilike(pattern)) | (SysMessage.content.ilike(pattern))
            )

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0

        query = query.order_by(SysMessage.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        messages = list((await db.execute(query)).scalars().all())

        # 批量获取发送人姓名
        sender_ids = list({m.sender_id for m in messages if m.sender_id})
        sender_map = await _get_user_display_map(db, sender_ids)

        items = [
            {
                "id": m.id,
                "receiver_id": m.receiver_id,
                "sender_id": m.sender_id,
                "sender_name": sender_map.get(m.sender_id),
                "title": m.title,
                "content": m.content,
                "msg_type": m.msg_type,
                "is_read": m.is_read,
                "read_time": _to_local_str(m.read_time),
                "relation_type": m.relation_type,
                "relation_id": m.relation_id,
                "created_at": _to_local_str(m.created_at),
            }
            for m in messages
        ]
        return {"list": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def get_unread_count(db: AsyncSession, receiver_id: int) -> dict:
        """获取未读消息统计"""
        total = (await db.execute(
            select(func.count(SysMessage.id))
            .where(
                SysMessage.receiver_id == receiver_id,
                SysMessage.is_read == False,
                SysMessage.deleted_at.is_(None),
                SysMessage.title.notilike("[已删除]%"),
            )
        )).scalar() or 0

        rows = (await db.execute(
            select(SysMessage.msg_type, func.count(SysMessage.id))
            .where(
                SysMessage.receiver_id == receiver_id,
                SysMessage.is_read == False,
                SysMessage.deleted_at.is_(None),
                SysMessage.title.notilike("[已删除]%"),
            )
            .group_by(SysMessage.msg_type)
        )).all()
        by_type = {row[0]: row[1] for row in rows}

        return {"total": total, "by_type": by_type}

    @staticmethod
    async def mark_as_read(db: AsyncSession, message_id: int, receiver_id: int) -> bool:
        """标记单条消息为已读"""
        msg = (await db.execute(
            select(SysMessage)
            .where(SysMessage.id == message_id, SysMessage.receiver_id == receiver_id)
        )).scalars().first()
        if not msg:
            return False
        msg.is_read = True
        msg.read_time = datetime.now()
        await db.flush()
        return True

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, receiver_id: int) -> int:
        """全部标记已读，返回影响行数"""
        result = await db.execute(
            update(SysMessage)
            .where(SysMessage.receiver_id == receiver_id, SysMessage.is_read == False)
            .values(is_read=True, read_time=datetime.now())
        )
        await db.flush()
        return result.rowcount

    @staticmethod
    async def create_message(
        db: AsyncSession,
        *,
        receiver_id: int,
        title: str,
        content: str | None = None,
        msg_type: str = "system",
        sender_id: int | None = None,
        relation_type: str | None = None,
        relation_id: int | None = None,
        is_broadcast: bool = False,
    ) -> SysMessage:
        """创建单条消息"""
        msg = SysMessage(
            receiver_id=receiver_id,
            sender_id=sender_id,
            title=title,
            content=content,
            msg_type=msg_type,
            relation_type=relation_type,
            relation_id=relation_id,
            is_broadcast=is_broadcast,
        )
        db.add(msg)
        await db.flush()
        return msg

    @staticmethod
    async def broadcast_message(
        db: AsyncSession,
        *,
        title: str,
        content: str,
        msg_type: str = "system",
        sender_id: int | None = None,
        target_scope: str = "all",
        target_ids: str | None = None,
        relation_type: str | None = None,
        relation_id: int | None = None,
    ) -> list[SysMessage]:
        """广播消息：根据范围向用户发送"""
        import json

        query = select(SysUser).where(SysUser.status == 1)

        if target_scope == "org" and target_ids:
            try:
                org_ids = json.loads(target_ids) if isinstance(target_ids, str) else target_ids
                staff_q = select(OrgStaff.user_id).where(
                    OrgStaff.org_id.in_(org_ids), OrgStaff.status == 1
                ).distinct()
                staff_rows = (await db.execute(staff_q)).all()
                user_ids = [row[0] for row in staff_rows if row[0]]
                if user_ids:
                    query = query.where(SysUser.id.in_(user_ids))
                else:
                    return []
            except (json.JSONDecodeError, Exception):
                pass

        elif target_scope == "role" and target_ids:
            try:
                role_ids = json.loads(target_ids) if isinstance(target_ids, str) else target_ids
                role_q = select(SysUserRole.user_id).where(
                    SysUserRole.role_id.in_(role_ids)
                ).distinct()
                role_rows = (await db.execute(role_q)).all()
                user_ids = [row[0] for row in role_rows if row[0]]
                if user_ids:
                    query = query.where(SysUser.id.in_(user_ids))
                else:
                    return []
            except (json.JSONDecodeError, Exception):
                pass

        elif target_scope == "staff" and target_ids:
            try:
                staff_ids = json.loads(target_ids) if isinstance(target_ids, str) else target_ids
                staff_q = select(OrgStaff.user_id).where(
                    OrgStaff.id.in_(staff_ids), OrgStaff.status == 1
                )
                staff_rows = (await db.execute(staff_q)).all()
                user_ids = [row[0] for row in staff_rows if row[0]]
                if user_ids:
                    query = query.where(SysUser.id.in_(user_ids))
                else:
                    return []
            except (json.JSONDecodeError, Exception):
                pass

        users = (await db.execute(query)).scalars().all()
        messages = []
        for user in users:
            msg = SysMessage(
                receiver_id=user.id,
                sender_id=sender_id,
                title=title,
                content=content,
                msg_type=msg_type,
                relation_type=relation_type,
                relation_id=relation_id,
                is_broadcast=True,
            )
            db.add(msg)
            messages.append(msg)

        if messages:
            await db.flush()
        return messages


class AnnouncementService:
    """公告服务"""

    @staticmethod
    async def get_announcements(
        db: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        is_active: bool | None = None,
    ) -> dict:
        """分页查询公告列表（排除已永久删除的）"""
        query = select(SysAnnouncement).where(SysAnnouncement.deleted_at.is_(None))

        if is_active is not None:
            query = query.where(SysAnnouncement.is_active == is_active)

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0

        query = query.order_by(SysAnnouncement.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        announcements = list((await db.execute(query)).scalars().all())

        publisher_ids = list({a.publisher_id for a in announcements})
        publisher_map = await _get_user_display_map(db, publisher_ids)

        items = [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "publisher_id": a.publisher_id,
                "publisher_name": publisher_map.get(a.publisher_id),
                "target_scope": a.target_scope,
                "target_ids": a.target_ids,
                "is_active": a.is_active,
                "created_at": _to_local_str(a.created_at),
                "updated_at": _to_local_str(a.updated_at),
            }
            for a in announcements
        ]
        return {"list": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def create_announcement(
        db: AsyncSession,
        *,
        title: str,
        content: str,
        publisher_id: int,
        target_scope: str = "all",
        target_ids: str | None = None,
    ) -> SysAnnouncement:
        """发布公告，并同步发送消息通知"""
        ann = SysAnnouncement(
            title=title,
            content=content,
            publisher_id=publisher_id,
            target_scope=target_scope,
            target_ids=target_ids,
        )
        db.add(ann)
        await db.flush()
        await db.refresh(ann)

        # 向目标范围用户发送消息通知
        await MessageService.broadcast_message(
            db,
            title=f"新公告：{title}",
            content=content[:500],
            msg_type="system",
            sender_id=publisher_id,
            target_scope=target_scope,
            target_ids=target_ids,
            relation_type="announcement",
            relation_id=ann.id,
        )

        return ann

    @staticmethod
    async def update_announcement(db: AsyncSession, ann_id: int, data: dict) -> dict | None:
        """编辑公告"""
        ann = (await db.execute(
            select(SysAnnouncement).where(
                SysAnnouncement.id == ann_id,
                SysAnnouncement.deleted_at.is_(None),
            )
        )).scalars().first()
        if not ann:
            return None
        for key, value in data.items():
            if value is not None and hasattr(ann, key):
                setattr(ann, key, value)
        await db.flush()
        await db.refresh(ann)
        return {
            "id": ann.id,
            "title": ann.title,
            "content": ann.content,
            "publisher_id": ann.publisher_id,
            "target_scope": ann.target_scope,
            "target_ids": ann.target_ids,
            "is_active": ann.is_active,
            "created_at": _to_local_str(ann.created_at),
            "updated_at": _to_local_str(ann.updated_at),
        }

    @staticmethod
    async def withdraw_announcement(db: AsyncSession, ann_id: int) -> bool:
        """撤回公告（设为无效，仍可在列表中显示）"""
        ann = (await db.execute(
            select(SysAnnouncement).where(
                SysAnnouncement.id == ann_id,
                SysAnnouncement.deleted_at.is_(None),
            )
        )).scalars().first()
        if not ann:
            return False
        if not ann.is_active:
            return False  # 已撤回，不可重复撤回

        ann.is_active = False

        # 将关联消息标题标记为已撤回
        related = (await db.execute(
            select(SysMessage).where(
                SysMessage.relation_type == "announcement",
                SysMessage.relation_id == ann_id,
                SysMessage.deleted_at.is_(None),
            )
        )).scalars().all()
        for msg in related:
            msg.title = f"[已撤回] {msg.title}"

        await db.flush()
        return True

    @staticmethod
    async def delete_announcement(db: AsyncSession, ann_id: int) -> bool:
        """永久隐藏公告（仅已撤回的可删除，前端不可见，DB 保留记录）"""
        ann = (await db.execute(
            select(SysAnnouncement).where(
                SysAnnouncement.id == ann_id,
                SysAnnouncement.deleted_at.is_(None),
            )
        )).scalars().first()
        if not ann:
            return False

        ann.deleted_at = datetime.now()
        ann.is_active = False

        # 关联的消息通知也标记为已删除（前端任何地方不可见）
        related = (await db.execute(
            select(SysMessage).where(
                SysMessage.relation_type == "announcement",
                SysMessage.relation_id == ann_id,
                SysMessage.deleted_at.is_(None),
            )
        )).scalars().all()
        for msg in related:
            msg.deleted_at = datetime.now()

        await db.flush()
        return True


# ========== 私有辅助函数 ==========

async def get_admin_receive_all_config(db: AsyncSession) -> bool:
    """读取管理员接收全部通知开关配置"""
    from app.models.audit_log import SysConfig
    config = (await db.execute(
        select(SysConfig).where(SysConfig.config_key == "admin_receive_all_notifications")
    )).scalars().first()
    if not config:
        return True  # 默认开启
    return config.config_value == "true"


async def get_admin_user_ids(db: AsyncSession) -> list[int]:
    """获取所有管理员用户ID列表"""
    from app.models import SysRole, SysUserRole
    admin_roles = (await db.execute(
        select(SysRole).where(SysRole.code.in_(["admin"]))
    )).scalars().all()
    if not admin_roles:
        return []
    role_ids = [r.id for r in admin_roles]
    rows = (await db.execute(
        select(SysUserRole.user_id).where(SysUserRole.role_id.in_(role_ids)).distinct()
    )).all()
    return [row[0] for row in rows if row[0]]


async def notify_admins_extra(
    db: AsyncSession,
    *,
    title: str,
    content: str,
    msg_type: str = "system",
    sender_id: int | None = None,
    relation_type: str | None = None,
    relation_id: int | None = None,
    exclude_user_ids: set[int] | None = None,
):
    """如果管理员接收全部通知开关开启，给所有管理员补发通知"""
    if not await get_admin_receive_all_config(db):
        return

    admin_ids = await get_admin_user_ids(db)
    if not admin_ids:
        return

    exclude = exclude_user_ids or set()
    for uid in admin_ids:
        if uid in exclude:
            continue
        await MessageService.create_message(
            db,
            receiver_id=uid,
            title=title,
            content=content,
            msg_type=msg_type,
            sender_id=sender_id,
            relation_type=relation_type,
            relation_id=relation_id,
        )


async def _get_user_display_map(db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
    """获取 用户ID → 显示名称 映射（优先 staff.name，其次 username）"""
    if not user_ids:
        return {}

    users = (await db.execute(
        select(SysUser).where(SysUser.id.in_(user_ids))
    )).scalars().all()

    staff_ids = [u.staff_id for u in users if u.staff_id]
    staff_map: dict[int, str] = {}
    if staff_ids:
        rows = (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(staff_ids))
        )).all()
        staff_map = {row[0]: row[1] for row in rows}

    result: dict[int, str] = {}
    for u in users:
        if u.staff_id and u.staff_id in staff_map:
            result[u.id] = staff_map[u.staff_id]
        else:
            result[u.id] = u.username
    return result
