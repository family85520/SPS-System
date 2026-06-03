from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime


VALID_ROLE_TYPES = ("role", "tag")


class RoleCreate(BaseModel):
    """创建角色"""
    name: str
    code: str
    role_type: str = "role"
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

    @field_validator("role_type")
    @classmethod
    def validate_role_type(cls, v: str) -> str:
        if v not in VALID_ROLE_TYPES:
            raise ValueError(f"角色类型必须是 {'/'.join(VALID_ROLE_TYPES)}")
        return v

    @model_validator(mode="after")
    def validate_tag_no_permissions(self):
        if self.role_type == "tag" and self.permissions:
            self.permissions = None
        return self


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = None
    role_type: Optional[str] = None
    permissions: Optional[dict] = None

    @field_validator("role_type")
    @classmethod
    def validate_role_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROLE_TYPES:
            raise ValueError(f"角色类型必须是 {'/'.join(VALID_ROLE_TYPES)}")
        return v

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
    role_type: str = "role"
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


class StaffTagAssign(BaseModel):
    """为人员分配标识"""
    role_ids: list[int]

    @field_validator("role_ids")
    @classmethod
    def validate_role_ids(cls, v: list[int]) -> list[int]:
        return v
