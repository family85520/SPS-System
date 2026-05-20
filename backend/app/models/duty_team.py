"""值班组模型"""

from sqlalchemy import String, SmallInteger, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class SchDutyTeam(Base, TimestampMixin):
    """值班组 - 按组排班"""
    __tablename__ = "sch_duty_team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shift_template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sch_shift_template.id"), nullable=False, comment="所属班次模板ID"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="值班组名称，如：白班A组")
    staff_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]", comment="组内人员ID列表JSON")
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False, comment="优先级，数字越小越优先")
    enabled: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="是否启用 1=是 0=否")

    shift_template: Mapped["SchShiftTemplate"] = relationship(backref="duty_teams")  # type: ignore[name-defined]

    @property
    def staff_id_list(self) -> list[int]:
        """解析后的组内人员 ID 列表。"""
        import json
        try:
            return json.loads(self.staff_ids) if isinstance(self.staff_ids, str) else (self.staff_ids or [])
        except (json.JSONDecodeError, TypeError):
            return []
