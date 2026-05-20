from __future__ import annotations

from datetime import date as _date, datetime as _datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== SchSchedule Schema ====================

class ScheduleCreate(BaseModel):
    """创建排班记录（单日单班次）"""
    date: _date = Field(..., description="排班日期")
    shift_id: int = Field(..., gt=0, description="班次模板ID")
    org_id: int = Field(..., gt=0, description="组织ID")
    leader_staff_id: Optional[int] = Field(None, description="值班领导人员ID")
    status: int = Field(default=0, description="0=草稿 1=已发布 2=已撤回")
    source: str = Field(default="manual", description="生成方式 auto/manual/swap")


class ScheduleUpdate(BaseModel):
    """更新排班记录（仅草稿可更新）"""
    date: Optional[_date] = None
    shift_id: Optional[int] = Field(None, gt=0)
    org_id: Optional[int] = Field(None, gt=0)
    leader_staff_id: Optional[int] = None


# ==================== SchScheduleDetail Schema ====================

class ScheduleDetailCreate(BaseModel):
    """创建排班明细"""
    staff_id: int = Field(..., gt=0, description="人员ID")
    role_type: str = Field(default="member", description="角色类型 leader/member")
    is_substitute: bool = Field(default=False, description="是否替班")
    note: Optional[str] = Field(None, max_length=200, description="备注")


class ScheduleDetailUpdate(BaseModel):
    """更新排班明细"""
    staff_id: Optional[int] = Field(None, gt=0)
    role_type: Optional[str] = None
    is_substitute: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=200)


class AssignStaffRequest(BaseModel):
    """为排班分配人员"""
    staff_id: int = Field(..., gt=0, description="人员ID")
    role_type: str = Field(default="member", description="角色类型 leader/member")
    is_substitute: bool = Field(default=False, description="是否替班")
    note: Optional[str] = None


class RemoveStaffRequest(BaseModel):
    """移除排班中的人员"""
    staff_id: int = Field(..., gt=0, description="人员ID")


class BatchDetailItem(BaseModel):
    """批量操作单条明细"""
    id: Optional[int] = Field(None, description="明细ID，有则更新无则创建")
    schedule_id: int = Field(..., gt=0)
    staff_id: int = Field(..., gt=0)
    role_type: str = "member"
    is_substitute: bool = False
    note: Optional[str] = None


class BatchDetailRequest(BaseModel):
    """批量创建/更新排班明细"""
    items: list[BatchDetailItem]


class BatchPublishRequest(BaseModel):
    """批量发布/撤回排班"""
    schedule_ids: list[int] = Field(..., min_length=1, description="排班记录ID列表")


# ==================== 响应 Schema ====================

class StaffInfo(BaseModel):
    """人员信息"""
    staff_id: int
    name: str
    role_type: str = "member"
    is_substitute: bool = False
    note: Optional[str] = None


class ShiftInfo(BaseModel):
    """班次信息"""
    shift_id: int
    shift_name: str
    shift_color: str = ""
    start_time: str = ""
    end_time: str = ""


class ScheduleDetailResponse(BaseModel):
    """排班明细响应"""
    id: int
    schedule_id: int
    staff_id: int
    staff_name: Optional[str] = None
    role_type: str
    is_substitute: bool = False
    note: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduleResponse(BaseModel):
    """排班记录响应（含明细）"""
    id: int
    date: _date
    shift_id: int
    shift_name: Optional[str] = None
    shift_color: Optional[str] = None
    shift_start_time: Optional[str] = None
    shift_end_time: Optional[str] = None
    org_id: int
    org_name: Optional[str] = None
    leader_staff_id: Optional[int] = None
    leader_name: Optional[str] = None
    status: int
    source: str
    published_at: Optional[_datetime] = None
    published_by: Optional[int] = None
    created_at: Optional[_datetime] = None
    updated_at: Optional[_datetime] = None
    details: list[ScheduleDetailResponse] = []

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """排班列表响应"""
    items: list[ScheduleResponse]
    total: int


# ==================== 日历视图 ====================

class CalendarShift(BaseModel):
    """日历中的单个班次"""
    schedule_id: int
    shift_template_id: int
    shift_name: str
    shift_color: str = ""
    start_time: str = ""
    end_time: str = ""
    leader: Optional[StaffInfo] = None
    members: list[StaffInfo] = []
    status: int = 0
    source: str = "manual"
    conflicts: list[str] = []


class CalendarDate(BaseModel):
    """日历中单天的数据"""
    date: str
    shifts: list[CalendarShift] = []


class CalendarResponse(BaseModel):
    """排班日历响应"""
    dates: list[CalendarDate] = []


# ==================== 人员排班统计 ====================

class StaffShiftStat(BaseModel):
    """人员单日排班信息"""
    date: _date
    shift_name: str
    shift_color: str = ""
    start_time: str = ""
    end_time: str = ""
    role_type: str = "member"


class StaffSummaryResponse(BaseModel):
    """人员排班统计响应"""
    staff_id: int
    total_days: int = 0
    total_hours: float = 0.0
    night_shifts: int = 0
    recent_shifts: list[StaffShiftStat] = []
