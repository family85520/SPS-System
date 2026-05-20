from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=4, max_length=100, description="密码")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    roles: List[str]
    must_change_password: bool = False


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    status: int
    roles: List[str]
    permissions: dict
    last_login_at: Optional[datetime] = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    """修改密码"""
    old_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=4, max_length=100)


class ForceChangePasswordRequest(BaseModel):
    """首次登录强制修改密码"""
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")
