"""导出 API 路由"""

from __future__ import annotations

from datetime import date as date_type
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permissions
from app.models import SysUser
from app.models.audit_log import SysConfig
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["数据导出"])


def _parse(date_str: str, field: str) -> date_type:
    try:
        return date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, f"{field} 格式错误，应为 YYYY-MM-DD")


def _content_disposition(filename: str) -> str:
    """生成兼容中文的 Content-Disposition 头（RFC 5987）"""
    ascii_fallback = "export"
    encoded = quote(filename, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\''  + encoded


@router.get("/schedule/excel", summary="导出排班表 Excel")
async def export_schedule_excel(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID"),
    dimension: str = Query("org", description="维度：org=按组织 / person=按人员"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "read")),
):
    sd, ed = _parse(start_date, "start_date"), _parse(end_date, "end_date")
    if ed < sd:
        raise HTTPException(400, "结束日期不能早于开始日期")

    try:
        buf = await ExportService.schedule_excel(db, sd, ed, org_id, dimension)
    except ValueError as e:
        raise HTTPException(404, str(e))

    suffix = "按人员" if dimension == "person" else "按组织"
    filename = f"排班表({suffix})_{start_date}_{end_date}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/schedule/pdf", summary="导出排班表 PDF")
async def export_schedule_pdf(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID"),
    dimension: str = Query("org", description="维度：org=按组织 / person=按人员"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "read")),
):
    sd, ed = _parse(start_date, "start_date"), _parse(end_date, "end_date")
    if ed < sd:
        raise HTTPException(400, "结束日期不能早于开始日期")

    # 读取单位名称
    unit_cfg = (await db.execute(
        select(SysConfig).where(SysConfig.config_key == "unit_name")
    )).scalars().first()
    unit_name = unit_cfg.config_value if unit_cfg else ""

    try:
        buf = await ExportService.schedule_pdf(db, sd, ed, org_id, unit_name, dimension)
    except ValueError as e:
        raise HTTPException(404, str(e))

    suffix = "按人员" if dimension == "person" else "按组织"
    filename = f"排班表({suffix})_{start_date}_{end_date}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/statistics/excel", summary="导出统计报表 Excel")
async def export_statistics_excel(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "read")),
):
    sd, ed = _parse(start_date, "start_date"), _parse(end_date, "end_date")
    if ed < sd:
        raise HTTPException(400, "结束日期不能早于开始日期")

    try:
        buf = await ExportService.statistics_excel(db, sd, ed, org_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    filename = f"排班统计_{start_date}_{end_date}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/statistics/pdf", summary="导出统计报表 PDF")
async def export_statistics_pdf(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    org_id: int | None = Query(None, description="组织ID"),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "read")),
):
    sd, ed = _parse(start_date, "start_date"), _parse(end_date, "end_date")
    if ed < sd:
        raise HTTPException(400, "结束日期不能早于开始日期")

    try:
        buf = await ExportService.statistics_pdf(db, sd, ed, org_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    filename = f"排班统计_{start_date}_{end_date}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(filename)},
    )
