"""消息系统数据模型
包含：系统消息(sch_message) + 公告(sch_announcement)
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class SysMessage(Base, TimestampMixin):
    """系统消息表"""
    __tablename__ = "sch_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    receiver_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="接收人")
    sender_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=True, comment="发送人（系统消息为空）")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="消息标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="消息内容")
    msg_type: Mapped[str] = mapped_column(String(20), nullable=False, default="system", comment="消息类型：schedule/swap/approve/system")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否已读")
    read_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="阅读时间")
    relation_type: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="关联类型：schedule/swap_request/announcement")
    relation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="关联业务ID")
    is_broadcast: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否广播消息")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="永久隐藏时间（软删除标记）")

    # 关系（字符串引用，SQLAlchemy 延迟解析）
    receiver = relationship("SysUser", foreign_keys=[receiver_id], lazy="selectin")
    sender = relationship("SysUser", foreign_keys=[sender_id], lazy="selectin")

    __table_args__ = (
        Index("ix_sch_message_receiver_read_time", "receiver_id", "is_read", "created_at"),
        {"comment": "系统消息表"},
    )


class SysAnnouncement(Base, TimestampMixin):
    """公告表"""
    __tablename__ = "sch_announcement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="公告标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="公告内容")
    publisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=False, comment="发布人")
    target_scope: Mapped[str] = mapped_column(String(20), default="all", nullable=False, comment="目标范围：all/org/role")
    target_ids: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="目标ID列表（JSON字符串）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否有效（False=已撤回）")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="永久隐藏时间（软删除标记）")

    publisher = relationship("SysUser", lazy="selectin")

    __table_args__ = ({"comment": "公告表"},)
