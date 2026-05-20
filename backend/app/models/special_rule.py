from datetime import date
from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin


class SchSpecialRule(Base, TimestampMixin):
    __tablename__ = "sch_special_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey("org_staff.id"), nullable=False, index=True, comment="关联人员ID")
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="规则类型")
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="规则参数")
    effective_from: Mapped[date | None] = mapped_column(nullable=True, comment="生效开始日期")
    effective_to: Mapped[date | None] = mapped_column(nullable=True, comment="生效结束日期")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="规则备注")

    staff = relationship("OrgStaff", back_populates="special_rules", lazy="selectin")
