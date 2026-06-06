from pydantic import BaseModel
from typing import Optional


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    system_name: str = "排班管理系统"
    org_name: str = ""
    swap_approval_enabled: bool = True
    schedule_approval_enabled: bool = False
    admin_receive_all_notifications: str = "true"
    auto_schedule_enabled: str = "false"
    auto_schedule_status: str = "draft"
    auto_schedule_last_run: str = ""
    auto_schedule_time: str = "23:00"
    auto_schedule_org_ids: list[int] = []
    auto_schedule_shift_ids: list[int] = []
    auto_schedule_skip_existing: str = "false"


class SystemConfigUpdate(BaseModel):
    """系统配置更新"""
    system_name: Optional[str] = None
    org_name: Optional[str] = None
    swap_approval_enabled: Optional[bool] = None
    schedule_approval_enabled: Optional[bool] = None
    admin_receive_all_notifications: Optional[str] = None
    auto_schedule_enabled: Optional[str] = None
    auto_schedule_status: Optional[str] = None
    auto_schedule_time: Optional[str] = None
    auto_schedule_org_ids: Optional[list[int]] = None
    auto_schedule_shift_ids: Optional[list[int]] = None
    auto_schedule_skip_existing: Optional[str] = None
