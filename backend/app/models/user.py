from datetime import datetime
from sqlalchemy import String, SmallInteger, DateTime, ForeignKey, Boolean, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base
from app.models.base import TimestampMixin

class SysUser(Base, TimestampMixin):
    """用户表"""
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="登录用户名")
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False, comment="加密后的密码")
    staff_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("org_staff.id"), nullable=True, comment="关联人员ID")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="0=禁用 1=启用")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="首次登录必须修改密码")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最后登录时间")

    # 关系
    staff = relationship("OrgStaff", back_populates="user", lazy="selectin")
    roles = relationship("SysRole", secondary="sys_user_role", back_populates="users", lazy="selectin")


class SysRole(Base):
    """角色表"""
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名称")
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="角色编码")
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="权限列表")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否系统内置角色")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")

    # 关系
    users = relationship("SysUser", secondary="sys_user_role", back_populates="roles")


class SysUserRole(Base):
    """用户角色关联表"""
    __tablename__ = "sys_user_role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="用户ID")
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_role.id"), nullable=False, index=True, comment="角色ID")
