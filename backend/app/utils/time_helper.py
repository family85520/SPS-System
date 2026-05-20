"""公共时间转换工具模块（东八区 UTC+8）"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

TIMEZONE_OFFSET = timezone(timedelta(hours=8))


def utc_to_local(dt: datetime | None) -> datetime | None:
    """将 UTC datetime 转为本地时间 datetime 对象（东八区 UTC+8）"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TIMEZONE_OFFSET)


def to_local_str(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str | None:
    """将 UTC datetime 转为本地时间字符串"""
    if dt is None:
        return None
    local_dt = utc_to_local(dt)
    return local_dt.strftime(fmt)


def to_local_short(dt: datetime | None) -> str | None:
    """将 UTC datetime 转为本地时间短字符串（不含秒）"""
    return to_local_str(dt, fmt="%Y-%m-%d %H:%M")
