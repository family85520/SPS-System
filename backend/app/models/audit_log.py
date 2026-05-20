from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base

class SysAuditLog(Base):
    """操作日志表"""
    __tablename__ = "sys_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="操作人ID")
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="操作类型")
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作对象类型")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="操作对象ID")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="操作详情")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="操作人IP")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="操作时间")


class SysConfig(Base):
    """系统配置表"""
    __tablename__ = "sys_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(String(1000), nullable=False, comment="配置值")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="配置说明")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
