from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StaffCreate(BaseModel):
    """创建人员"""
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    employee_no: Optional[str] = Field(None, max_length=30, description="工号（留空自动生成）")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    org_id: int = Field(..., description="所属组织ID")
    tags: Optional[List[str]] = Field(None, description='特殊角色标签（同时用于分配系统角色）')
    available_posts: Optional[List[int]] = Field(None, description="可用岗位ID列表")
    create_account: bool = Field(True, description="是否同时创建登录账号，默认开启")
    must_change_password: bool = Field(True, description="首次登录是否需要修改密码，默认开启")
    tag_role_ids: Optional[List[int]] = Field(None, description="标识角色ID列表（新标识体系）")


class StaffUpdate(BaseModel):
    """更新人员"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    employee_no: Optional[str] = Field(None, min_length=1, max_length=30, description="工号")
    phone: Optional[str] = Field(None, max_length=20)
    org_id: Optional[int] = None
    status: Optional[int] = Field(None, description="1=在岗 2=请假 3=外派 0=停用")
    tags: Optional[List[str]] = None
    available_posts: Optional[List[int]] = None
    tag_role_ids: Optional[List[int]] = Field(None, description="标识角色ID列表（新标识体系）")


class StaffAccountUpdate(BaseModel):
    """更新人员关联的账号状态"""
    account_status: Optional[int] = Field(None, description="账号状态 1启用 0禁用")
    reset_password: Optional[str] = Field(None, min_length=6, max_length=100, description="重置密码（传入新密码）")
    role_ids: Optional[List[int]] = Field(None, description="重新分配角色")


class StaffResponse(BaseModel):
    """人员响应"""
    id: int
    name: str
    employee_no: str
    phone: Optional[str]
    org_id: int
    org_name: Optional[str] = None
    status: int
    tags: Optional[List[str]]
    available_posts: Optional[List[int]]
    # 新标识体系
    tag_roles: Optional[List[dict]] = None  # [{"id": 1, "name": "领导", "code": "leader"}, ...]
    # 账号信息
    has_account: bool = False
    account_username: Optional[str] = None
    account_status: Optional[int] = None
    account_roles: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StaffListResponse(BaseModel):
    """人员列表响应"""
    total: int
    items: List[StaffResponse]
