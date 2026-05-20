"""班次模板与轮换组模型"""

from sqlalchemy import String, SmallInteger, Integer, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin


# 排班模式枚举值（常量，避免魔法字符串）
SCHEDULE_MODE_INDIVIDUAL = "individual"
SCHEDULE_MODE_TEAM_ROTATION = "team_rotation"
SCHEDULE_MODE_ROTATION_GROUP = "rotation_group"

ROTATION_UNITS = ("day", "week", "month")
VALID_WEEKDAYS = list(range(1, 8))  # 1=周一 ~ 7=周日


class SchShiftTemplate(Base, TimestampMixin):
    """班次模板表"""
    __tablename__ = "sch_shift_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="班次名称")
    org_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("org_organization.id"), nullable=True, comment="所属组织，NULL为全局"
    )
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="起始时间 HH:MM")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="结束时间 HH:MM")
    duration_hours: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False, comment="班次时长（小时）")
    color: Mapped[str] = mapped_column(String(7), default="#409EFF", nullable=False, comment="颜色标识HEX")
    leader_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="值班领导最少人数")
    leader_max: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="值班领导最多人数")
    leader_pool: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="领导候选人员ID列表")
    member_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="值班人员最少人数")
    member_max: Mapped[int] = mapped_column(Integer, default=3, nullable=False, comment="值班人员最多人数")
    apply_days: Mapped[list] = mapped_column(
        JSON, default=VALID_WEEKDAYS, nullable=False, comment="适用日期周一~周日"
    )
    rotation_frequency: Mapped[str] = mapped_column(
        String(20), default="day", nullable=False, comment="整体轮换频次：day/week/month"
    )
    schedule_mode: Mapped[str] = mapped_column(
        String(20), default=SCHEDULE_MODE_INDIVIDUAL, nullable=False,
        comment="排班模式：individual/team_rotation/rotation_group",
    )
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="0=停用 1=启用")

    # 轮换组关系（由 SchRotationGroup 的 backref 自动创建）

    # ---- 辅助属性 ----

    @property
    def is_night(self) -> bool:
        """是否夜班（20:00后开始 或 08:00前结束）。"""
        try:
            sh, _ = map(int, self.start_time.split(":"))
            eh, _ = map(int, self.end_time.split(":"))
            return sh >= 20 or eh <= 8
        except (ValueError, AttributeError):
            return False

    @property
    def effective_duration(self) -> float:
        """有效时长（小时），跨天自动 +24。"""
        try:
            sh, sm = map(int, self.start_time.split(":"))
            eh, em = map(int, self.end_time.split(":"))
            dur = (eh * 60 + em - sh * 60 - sm) / 60
            return dur + 24 if dur <= 0 else dur
        except (ValueError, AttributeError):
            return 0.0


class SchRotationGroup(Base):
    """班次轮换组 - 配置固定轮换人员"""
    __tablename__ = "sch_rotation_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shift_template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sch_shift_template.id"), nullable=False, comment="所属班次模板ID"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="轮换组名称")
    staff_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]", comment="轮换人员ID列表JSON")
    rotation_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="month", comment="轮换周期：day/week/month"
    )
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="该组占位数")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10, comment="优先级，数字越小越优先")
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="是否启用 1=是 0=否")

    shift_template: Mapped["SchShiftTemplate"] = relationship(
        backref="rotation_groups_list", lazy="selectin",
    )
