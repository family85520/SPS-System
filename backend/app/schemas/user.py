"""用户账号管理 Schema"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., min_length=3, max_length=50, description="登录账号")
    password: str = Field(..., min_length=6, max_length=100, description="登录密码")
    staff_id: Optional[int] = Field(None, description="关联人员ID")
    status: int = Field(1, description="状态 1启用 0禁用")
    role_ids: list[int] = Field(default_factory=list, description="角色ID列表")
    must_change_password: bool = Field(True, description="首次登录是否需要修改密码")
    # 同步创建人员
    create_staff: bool = Field(False, description="是否同步创建人员记录")
    staff_name: Optional[str] = Field(None, description="人员姓名（同步创建时必填）")
    employee_no: Optional[str] = Field(None, description="工号（同步创建时必填）")
    phone: Optional[str] = Field(None, description="联系电话")
    org_id: Optional[int] = Field(None, description="所属组织ID（同步创建时必填）")
    staff_tags: Optional[list[str]] = Field(None, description="角色标签")


class UserUpdate(BaseModel):
    """更新用户"""
    staff_id: Optional[int] = Field(None, description="关联人员ID")
    status: Optional[int] = Field(None, description="状态 1启用 0禁用")
    role_ids: Optional[list[int]] = Field(None, description="角色ID列表")


class ResetPasswordRequest(BaseModel):
    """重置密码"""
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    status: int
    roles: list[str] = []
    role_ids: list[int] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    items: list[UserResponse]
