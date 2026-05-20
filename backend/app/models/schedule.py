from datetime import date as _date, datetime as _datetime
from typing import Optional

from sqlalchemy import String, SmallInteger, Integer, ForeignKey, Date, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class SchSchedule(Base, TimestampMixin):
    """排班记录表"""
    __tablename__ = "sch_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    date: Mapped[_date] = mapped_column(Date, nullable=False, index=True, comment="排班日期")
    shift_id: Mapped[int] = mapped_column(Integer, ForeignKey("sch_shift_template.id"), nullable=False, comment="班次模板ID")
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("org_organization.id"), nullable=False, index=True, comment="组织ID")
    leader_staff_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("org_staff.id"), nullable=True, comment="值班领导人员ID")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment="0=草稿 1=已发布 2=已撤回")
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False, comment="生成方式 auto/manual/swap")
    published_at: Mapped[Optional[_datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="发布时间")
    published_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=True, comment="发布人ID")

    # 状态常量
    STATUS_DRAFT = 0          # 草稿
    STATUS_PUBLISHED = 1      # 已发布
    STATUS_RECALLED = 2       # 已撤回
    STATUS_PENDING_APPROVE = 3  # 待审核

    # 不可编辑的状态集合
    LOCKED_STATUSES = {1, 3}  # 已发布、待审核不可直接修改
    EDITABLE_STATUSES = {0, 2}  # 草稿、已撤回可以编辑
    DELETABLE_STATUSES = {0, 2}  # 草稿、已撤回可以删除

    # 关系
    details = relationship("SchScheduleDetail", back_populates="schedule", lazy="selectin", cascade="all, delete-orphan")
    leader = relationship("OrgStaff", foreign_keys=[leader_staff_id], lazy="selectin")
    shift = relationship("SchShiftTemplate", lazy="selectin")


class SchScheduleDetail(Base):
    """排班明细表"""
    __tablename__ = "sch_schedule_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("sch_schedule.id"), nullable=False, index=True, comment="排班记录ID")
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey("org_staff.id"), nullable=False, index=True, comment="人员ID")
    role_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色类型 leader/member")
    is_substitute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否替班标记")
    note: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="备注")

    # 关系
    schedule = relationship("SchSchedule", back_populates="details")
    staff = relationship("OrgStaff", lazy="selectin")
