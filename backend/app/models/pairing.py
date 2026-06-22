"""配对关系表 - 存储新老员工配对关系"""

from sqlalchemy import String, Integer, ARRAY, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import TimestampMixin


class SchPairing(Base, TimestampMixin):
    """配对关系表 - 存储新老员工配对关系"""
    __tablename__ = "sch_pairing"
    __table_args__ = (
        UniqueConstraint('org_id', 'shift_id', 'slot_index', 'group_type',
                         name='uq_pairing_slot'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="组织ID")
    shift_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="班次模板ID")
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="槽位索引 (0/1/2)")
    group_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="分组类型 day/night")
    staff_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, comment="配对人员ID")
    is_new: Mapped[list[bool]] = mapped_column(ARRAY(Boolean), nullable=False, comment="是否新员工")
