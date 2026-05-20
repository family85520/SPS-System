from sqlalchemy import String, SmallInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin


class OrgStaff(Base, TimestampMixin):
    """人员表"""
    __tablename__ = "org_staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    employee_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True, comment="工号")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("org_organization.id"), nullable=False, index=True, comment="所属组织ID")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1=在岗 2=请假 3=外派 0=停用")
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, comment='特殊角色标签 ["带班领导","新入职"]')
    available_posts: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="可用岗位列表")

    # 关系
    organization = relationship("OrgOrganization", back_populates="staffs", lazy="selectin")
    user = relationship("SysUser", back_populates="staff", uselist=False, lazy="selectin")
    special_rules = relationship("SchSpecialRule", back_populates="staff", lazy="selectin")
