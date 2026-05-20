from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ConstraintCreate(BaseModel):
    """创建约束规则"""
    rule_type: str
    rule_name: str
    params: dict = {}
    priority: int = 0
    scope_type: str = "all"
    scope_ids: Optional[list[int]] = None
    enabled: bool = True

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("规则类型不能为空")
        return v.strip()

    @field_validator("rule_name")
    @classmethod
    def validate_rule_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("规则名称不能为空")
        if len(v) > 100:
            raise ValueError("规则名称不能超过100个字符")
        return v

    @field_validator("scope_type")
    @classmethod
    def validate_scope_type(cls, v: str) -> str:
        if v not in ("all", "org"):
            raise ValueError("适用范围类型只能是 all 或 org")
        return v


class ConstraintUpdate(BaseModel):
    """更新约束规则（所有字段可选）"""
    rule_name: Optional[str] = None
    params: Optional[dict] = None
    priority: Optional[int] = None
    scope_type: Optional[str] = None
    scope_ids: Optional[list[int]] = None
    enabled: Optional[bool] = None

    @field_validator("scope_type")
    @classmethod
    def validate_scope_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("all", "org"):
            raise ValueError("适用范围类型只能是 all 或 org")
        return v


class ConstraintResponse(BaseModel):
    """约束规则响应"""
    id: int
    rule_type: str
    rule_name: str
    params: dict
    priority: int
    scope_type: str
    scope_ids: Optional[list[int]] = None
    enabled: bool
    is_preset: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchPriorityItem(BaseModel):
    """批量更新优先级的单项"""
    id: int
    priority: int


class BatchPriorityRequest(BaseModel):
    """批量更新优先级请求"""
    items: list[BatchPriorityItem]
