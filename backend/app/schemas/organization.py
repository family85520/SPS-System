from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OrgCreate(BaseModel):
    """创建组织"""
    name: str = Field(..., min_length=1, max_length=100, description="组织名称")
    parent_id: Optional[int] = Field(None, description="上级组织ID，为空则为顶级")
    code: Optional[str] = Field(None, max_length=50, description="部门代码（留空则自动生成）")
    sort_order: int = Field(0, description="排序序号")


class OrgUpdate(BaseModel):
    """更新组织"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50, description="部门代码")
    sort_order: Optional[int] = None
    status: Optional[int] = Field(None, description="0=停用 1=启用")


class OrgResponse(BaseModel):
    """组织响应"""
    id: int
    name: str
    code: Optional[str] = None
    parent_id: Optional[int]
    level: int
    sort_order: int
    status: int
    created_at: datetime
    updated_at: datetime
    children: List["OrgResponse"] = []

    class Config:
        from_attributes = True


class OrgTreeResponse(BaseModel):
    """组织树响应"""
    id: int
    name: str
    code: Optional[str] = None
    parent_id: Optional[int]
    level: int
    sort_order: int
    status: int
    staff_count: int = 0
    children: List["OrgTreeResponse"] = []

    class Config:
        from_attributes = True
