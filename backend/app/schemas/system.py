from pydantic import BaseModel
from typing import Optional


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    system_name: str = "排班管理系统"
    org_name: str = ""
    swap_approval_enabled: bool = True
    schedule_approval_enabled: bool = False
    admin_receive_all_notifications: str = "true"


class SystemConfigUpdate(BaseModel):
    """系统配置更新"""
    system_name: Optional[str] = None
    org_name: Optional[str] = None
    swap_approval_enabled: Optional[bool] = None
    schedule_approval_enabled: Optional[bool] = None
    admin_receive_all_notifications: Optional[str] = None
