from sqlalchemy import String, SmallInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class OrgOrganization(Base, TimestampMixin):
    __tablename__ = "org_organization"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="组织名称")
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("org_organization.id"), nullable=True, index=True, comment="上级组织ID"
    )
    level: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="层级深度")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="同级排序序号")
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True, comment="部门代码（自动生成，可编辑）")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="0=停用 1=启用")

    children = relationship("OrgOrganization", back_populates="parent", lazy="selectin")
    parent = relationship("OrgOrganization", back_populates="children", remote_side=[id], lazy="selectin")
    staffs = relationship("OrgStaff", back_populates="organization", lazy="selectin")
