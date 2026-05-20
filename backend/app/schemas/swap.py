"""调班管理 Schema"""

from __future__ import annotations

from datetime import date as _date, datetime as _datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求 Schema ====================

class SwapRequestCreate(BaseModel):
    """发起调班申请"""
    swap_type: str = Field(..., description="调班类型：specified（指定换班）/ open（开放换班）")
    requester_schedule_id: int = Field(..., gt=0, description="发起人的排班记录ID")
    target_id: Optional[int] = Field(None, description="被换人用户ID（指定换班时必填）")
    target_schedule_id: Optional[int] = Field(None, description="被换人的排班记录ID（指定换班时必填）")
    reason: Optional[str] = Field(None, max_length=500, description="申请原因")


class SwapApproveRequest(BaseModel):
    """审批调班申请"""
    approve_comment: Optional[str] = Field(None, max_length=500, description="审批意见")


# ==================== 响应 Schema ====================

class SwapRequestResponse(BaseModel):
    """调班申请响应"""
    id: int
    request_no: str
    swap_type: str
    requester_id: int
    requester_name: Optional[str] = None
    requester_schedule_id: int
    requester_schedule_date: Optional[_date] = None
    requester_shift_name: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    target_schedule_id: Optional[int] = None
    target_schedule_date: Optional[_date] = None
    target_shift_name: Optional[str] = None
    claimer_id: Optional[int] = None
    claimer_name: Optional[str] = None
    reason: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approver_name: Optional[str] = None
    approved_at: Optional[_datetime] = None
    approve_comment: Optional[str] = None
    created_at: Optional[_datetime] = None
    updated_at: Optional[_datetime] = None

    class Config:
        from_attributes = True


class SwapListResponse(BaseModel):
    """调班列表响应"""
    items: list[SwapRequestResponse]
    total: int
