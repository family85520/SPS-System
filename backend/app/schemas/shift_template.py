from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime


class ShiftTemplateCreate(BaseModel):
    """创建班次模板"""
    name: str
    org_id: Optional[int] = None
    start_time: str
    end_time: str
    color: str
    leader_min: int = 0
    leader_max: int = 0
    leader_pool: Optional[list[int]] = None
    member_min: int = 1
    member_max: int = 1
    apply_days: list[int]

    # ===== 排他性 =====
    allow_multi_template: bool = False

    # ===== 值班领导组 =====
    leader_enabled: bool = False
    leader_rotation_frequency: str = "week"
    leader_count: int = 1
    leader_use_tag: bool = True
    leader_tag_name: Optional[str] = None

    # ===== 值班组 =====
    member_enabled: bool = True
    member_rotation_frequency: str = "day"

    # ===== 特殊人员组 =====
    special_enabled: bool = False
    special_rotation_frequency: str = "month"
    special_count: int = 1
    special_pool: Optional[list[int]] = None
    special_exclude_from_member: bool = True

    constraint_ids: Optional[list[int]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("班次名称不能为空")
        if len(v) > 50:
            raise ValueError("班次名称不能超过50个字符")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return f"{h:02d}:{m:02d}"
        except Exception:
            raise ValueError("时间格式必须为 HH:MM")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        import re
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("颜色值必须为HEX格式，如 #FFD166")
        return v

    @field_validator("leader_min")
    @classmethod
    def validate_leader_min(cls, v: int) -> int:
        if v < 0:
            raise ValueError("值班领导最少人数不能小于0")
        return v

    @field_validator("leader_max")
    @classmethod
    def validate_leader_max(cls, v: int) -> int:
        if v < 0:
            raise ValueError("值班领导最多人数不能小于0")
        return v

    @field_validator("member_min")
    @classmethod
    def validate_member_min(cls, v: int) -> int:
        if v < 1:
            raise ValueError("值班人员最少人数不能小于1")
        return v

    @field_validator("member_max")
    @classmethod
    def validate_member_max(cls, v: int) -> int:
        if v < 1:
            raise ValueError("值班人员最多人数不能小于1")
        return v

    @field_validator("apply_days")
    @classmethod
    def validate_apply_days(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("适用日期不能为空")
        for d in v:
            if d < 1 or d > 7:
                raise ValueError("适用日期值必须在1-7之间（1=周一，7=周日）")
        return sorted(list(set(v)))

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.leader_max < self.leader_min:
            raise ValueError("值班领导最多人数不能小于最少人数")
        if self.member_max < self.member_min:
            raise ValueError("值班人员最多人数不能小于最少人数")

        # 校验时长为正数
        start_parts = self.start_time.split(":")
        end_parts = self.end_time.split(":")
        start_min = int(start_parts[0]) * 60 + int(start_parts[1])
        end_min = int(end_parts[0]) * 60 + int(end_parts[1])
        if end_min <= start_min:
            end_min += 24 * 60
        duration = (end_min - start_min) / 60
        if duration <= 0:
            raise ValueError("班次时长必须大于0")

        # 特殊人员组校验
        if self.special_enabled and (not self.special_pool or len(self.special_pool) == 0):
            raise ValueError("启用特殊人员组时必须指定候选人员")
        if self.special_count > 0 and self.special_pool and self.special_count > len(self.special_pool):
            raise ValueError("特殊组选出人数不能超过候选池大小")

        # 频次校验
        for freq_field in ("leader_rotation_frequency", "member_rotation_frequency", "special_rotation_frequency"):
            freq_val = getattr(self, freq_field, None)
            if freq_val is not None and freq_val not in ("day", "week", "month"):
                raise ValueError(f"{freq_field} 必须是 day/week/month")

        return self


class ShiftTemplateUpdate(BaseModel):
    """更新班次模板（所有字段可选）"""
    name: Optional[str] = None
    org_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    color: Optional[str] = None
    leader_min: Optional[int] = None
    leader_max: Optional[int] = None
    leader_pool: Optional[list[int]] = None
    member_min: Optional[int] = None
    member_max: Optional[int] = None
    apply_days: Optional[list[int]] = None

    # ===== 排他性 =====
    allow_multi_template: Optional[bool] = None

    # ===== 值班领导组 =====
    leader_enabled: Optional[bool] = None
    leader_rotation_frequency: Optional[str] = None
    leader_count: Optional[int] = None
    leader_use_tag: Optional[bool] = None
    leader_tag_name: Optional[str] = None

    # ===== 值班组 =====
    member_enabled: Optional[bool] = None
    member_rotation_frequency: Optional[str] = None

    # ===== 特殊人员组 =====
    special_enabled: Optional[bool] = None
    special_rotation_frequency: Optional[str] = None
    special_count: Optional[int] = None
    special_pool: Optional[list[int]] = None
    special_exclude_from_member: Optional[bool] = None

    constraint_ids: Optional[list[int]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("班次名称不能为空")
            if len(v) > 50:
                raise ValueError("班次名称不能超过50个字符")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                parts = v.split(":")
                if len(parts) != 2:
                    raise ValueError
                h, m = int(parts[0]), int(parts[1])
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
                return f"{h:02d}:{m:02d}"
            except Exception:
                raise ValueError("时间格式必须为 HH:MM")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import re
            if not re.match(r"^#[0-9a-fA-F]{6}$", v):
                raise ValueError("颜色值必须为HEX格式，如 #FFD166")
        return v

    @field_validator("apply_days")
    @classmethod
    def validate_apply_days(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is not None:
            if not v:
                raise ValueError("适用日期不能为空")
            for d in v:
                if d < 1 or d > 7:
                    raise ValueError("适用日期值必须在1-7之间")
            return sorted(list(set(v)))
        return v


class ShiftTemplateResponse(BaseModel):
    """班次模板响应"""
    id: int
    name: str
    org_id: Optional[int] = None
    start_time: str
    end_time: str
    duration_hours: float
    color: str
    leader_min: int
    leader_max: int
    leader_pool: Optional[list[int]] = None
    member_min: int
    member_max: int
    apply_days: list[int]
    status: int

    # ===== 排他性 =====
    allow_multi_template: bool = False

    # ===== 值班领导组 =====
    leader_enabled: bool = False
    leader_rotation_frequency: Optional[str] = "week"
    leader_count: int = 1
    leader_use_tag: bool = True
    leader_tag_name: Optional[str] = None

    # ===== 值班组 =====
    member_enabled: bool = True
    member_rotation_frequency: Optional[str] = "day"

    # ===== 特殊人员组 =====
    special_enabled: bool = False
    special_rotation_frequency: Optional[str] = "month"
    special_count: int = 1
    special_pool: Optional[list[int]] = None
    special_exclude_from_member: bool = True

    constraint_ids: Optional[list[int]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== 值班组 Schema ====================

class DutyTeamCreate(BaseModel):
    """值班组创建/更新"""
    name: str
    staff_ids: list[int] = []
    priority: int = 10
    enabled: bool = True


class DutyTeamResponse(BaseModel):
    """值班组响应"""
    id: int
    shift_template_id: int
    name: str
    staff_ids: list[int]
    priority: int
    enabled: bool

    @field_validator("staff_ids", mode="before")
    @classmethod
    def parse_staff_ids(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v):
        return bool(v)
