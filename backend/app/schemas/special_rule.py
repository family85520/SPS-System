from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class SpecialRuleCreate(BaseModel):
    """创建特殊排班规则"""
    staff_id: int
    rule_type: str
    params: dict = {}
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    reason: Optional[str] = None

    @field_validator("staff_id")
    @classmethod
    def validate_staff_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("人员ID必须大于0")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        valid_types = [
            "exclude_shift", "include_shift", "exclude_post",
            "must_pair", "exclude_date", "exclude_weekday",
        ]
        if v not in valid_types:
            raise ValueError(f"规则类型必须是以下之一: {', '.join(valid_types)}")
        return v

    @field_validator("effective_to")
    @classmethod
    def validate_effective_to(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get("effective_from") and v < info.data["effective_from"]:
            raise ValueError("结束日期不能早于开始日期")
        return v


class SpecialRuleUpdate(BaseModel):
    """更新特殊排班规则"""
    rule_type: Optional[str] = None
    params: Optional[dict] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    reason: Optional[str] = None

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_types = [
                "exclude_shift", "include_shift", "exclude_post",
                "must_pair", "exclude_date", "exclude_weekday",
            ]
            if v not in valid_types:
                raise ValueError(f"规则类型必须是以下之一: {', '.join(valid_types)}")
        return v


class SpecialRuleResponse(BaseModel):
    """特殊排班规则响应"""
    id: int
    staff_id: int
    rule_type: str
    params: Optional[dict] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
