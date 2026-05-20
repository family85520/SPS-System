"""消息系统 Pydantic Schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BroadcastRequest(BaseModel):
    """广播消息请求体"""
    title: str = Field(..., min_length=1, max_length=200, description="消息标题")
    content: str = Field(..., min_length=1, description="消息内容")
    msg_type: str = Field(default="system", description="消息类型")
    target_scope: str = Field(default="all", description="目标范围：all/org/role/staff")
    target_ids: Optional[str] = Field(default=None, description="目标ID列表")
    relation_type: Optional[str] = Field(default=None, description="关联类型")
    relation_id: Optional[int] = Field(default=None, description="关联业务ID")


class AnnouncementCreate(BaseModel):
    """发布公告请求体"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    target_scope: str = Field(default="all", description="目标范围：all/org/role/staff")
    target_ids: Optional[str] = None


class AnnouncementUpdate(BaseModel):
    """编辑公告请求体"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    is_active: Optional[bool] = None
