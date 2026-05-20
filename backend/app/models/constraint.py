from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin


class SchConstraint(Base, TimestampMixin):
    """约束规则表"""
    __tablename__ = "sch_constraint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="规则类型编码")
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规则名称")
    params: Mapped[dict] = mapped_column(JSON, nullable=False, comment="规则参数")
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="优先级（数字越小越优先）")
    scope_type: Mapped[str] = mapped_column(String(20), default="all", nullable=False, comment="适用范围类型 all/org")
    scope_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="适用范围ID列表")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否系统预置规则")
