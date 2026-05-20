from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class SchSwapRequest(Base, TimestampMixin):
    """调班申请表"""
    __tablename__ = "sch_swap_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    request_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True, comment="申请编号")
    swap_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="调班类型 specified/open")
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="发起人ID")
    requester_schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("sch_schedule.id"), nullable=False, comment="发起人的排班记录ID")
    target_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=True, comment="被换人ID")
    target_schedule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sch_schedule.id"), nullable=True, comment="被换人的排班记录ID")
    claimer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=True, comment="认领人ID")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="申请原因")
    status: Mapped[str] = mapped_column(String(20), default="pending_confirm", nullable=False, comment="状态")
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=True, comment="审批人ID")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审批时间")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="对方确认时间")
    refused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="对方拒绝时间")
    refuse_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="对方拒绝原因")
    approve_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")

    # 关系
    requester = relationship("SysUser", foreign_keys=[requester_id], lazy="selectin")
    target = relationship("SysUser", foreign_keys=[target_id], lazy="selectin")
    claimer = relationship("SysUser", foreign_keys=[claimer_id], lazy="selectin")
    approver = relationship("SysUser", foreign_keys=[approved_by], lazy="selectin")
