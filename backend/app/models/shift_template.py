"""班次模板模型"""

from sqlalchemy import String, SmallInteger, Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin


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
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="0=停用 1=启用")

    # ===== 排他性控制 =====
    allow_multi_template: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否允许本模板人员同日参与其他模板")

    # ===== 值班领导组 =====
    leader_enabled: Mapped[bool] = mapped_column(default=False, nullable=False, comment="值班领导组开关")
    leader_rotation_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="领导组轮换频次：day/week/month")
    leader_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="领导组每次选出人数")
    leader_use_tag: Mapped[bool] = mapped_column(default=True, nullable=False, comment="领导候选池为空时是否回退到标识人员")
    leader_tag_name: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="标识领导的身份标签名，默认'领导'；仅 leader_use_tag=True 时生效")

    # ===== 值班组 =====
    member_enabled: Mapped[bool] = mapped_column(default=True, nullable=False, comment="值班人员组开关")
    member_rotation_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="人员组轮换频次：day/week/month")

    # ===== 特殊人员组 =====
    special_enabled: Mapped[bool] = mapped_column(default=False, nullable=False, comment="特殊人员组开关")
    special_rotation_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="特殊组轮换频次：day/week/month")
    special_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="特殊组每次选出人数")
    special_pool: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="特殊人员候选ID列表")
    special_exclude_from_member: Mapped[bool] = mapped_column(default=True, nullable=False, comment="特殊人员是否从值班人员池排除")

    # ===== 约束规则选择 =====
    constraint_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="关联约束规则ID列表，NULL则使用全部规则")

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
