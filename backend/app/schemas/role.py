from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class RoleCreate(BaseModel):
    """创建角色"""
    name: str
    code: str
    permissions: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("角色名称不能为空")
        if len(v) > 50:
            raise ValueError("角色名称不能超过50个字符")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("角色编码不能为空")
        if len(v) > 30:
            raise ValueError("角色编码不能超过30个字符")
        return v


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = None
    permissions: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("角色名称不能为空")
            if len(v) > 50:
                raise ValueError("角色名称不能超过50个字符")
        return v


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    code: str
    permissions: Optional[dict] = None
    is_system: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserRoleAssign(BaseModel):
    """分配用户角色"""
    role_ids: list[int]

    @field_validator("role_ids")
    @classmethod
    def validate_role_ids(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("至少选择一个角色")
        return v
