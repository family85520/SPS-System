"""导出 API 路由"""

from __future__ import annotations

from datetime import date as date_type
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permissions, get_current_user
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

    suffix = "按人员" if dimension == "person" else "值班安排表"
    filename = f"{suffix}_{start_date}_{end_date}.xlsx"
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


# ==================== 导出模板管理 ====================

from fastapi import UploadFile, File, Form

@router.get("/templates/variables", summary="获取可用的模板变量列表")
async def get_template_variables(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """返回所有可用于自定义模板的变量及说明。所有班次统一使用 shift_N_* 格式。

    仅对「按组织维度导出 Excel」生效，PDF / 按人员 / 统计报表不适用。
    """
    from app.services.export_service import ExportService as ES
    shift_names = await ES.get_active_shift_names(db)
    variables = [
        {"name": "{{title}}",     "desc": "标题",         "category": "全局", "example": "XX组织日常值班工作安排表"},
        {"name": "{{org_name}}",  "desc": "组织名称",       "category": "全局", "example": "A组织"},
        {"name": "{{start_date}}","desc": "开始日期",       "category": "全局", "example": "2026-06-01"},
        {"name": "{{end_date}}",  "desc": "结束日期",       "category": "全局", "example": "2026-06-30"},
        {"name": "{{duty_text}}", "desc": "岗位职责说明",    "category": "全局", "example": "排班人员：全体监管人员（除...）"},
        {"name": "{{footer}}",    "desc": "页脚签名行",      "category": "全局", "example": "分管领导： 科室负责人： 制表人："},
        {"name": "{{date}}",      "desc": "日期（循环行）",  "category": "每日循环", "example": "2026-06-01"},
        {"name": "{{weekday}}",   "desc": "星期（循环行）",  "category": "每日循环", "example": "周一"},
        {"name": "{{duty_leader}}","desc": "值班领导（身份标识）","category": "每日循环", "example": "吴九"},
        {"name": "{{#each dates}}","desc": "循环标记",      "category": "控制", "example": "放在行首，该行按每天重复"},
        {"name": "{{#static}}",  "desc": "静态标记",      "category": "控制", "example": "放在单元格开头，该列全月取值统一（取首日解析结果）"},
    ]
    for i, sn in enumerate(shift_names):
        # 索引写法
        variables.append({"name": f"{{{{shift_{i}_name}}}}",    "desc": sn + " — 名称",     "category": f"shift_{i}（索引）/ " + sn, "example": sn})
        variables.append({"name": f"{{{{shift_{i}_time}}}}",    "desc": sn + " — 时段",     "category": f"shift_{i}（索引）/ " + sn, "example": "08:30-19:00"})
        variables.append({"name": f"{{{{shift_{i}_leader}}}}",  "desc": sn + " — 值班组长", "category": f"shift_{i}（索引）/ " + sn, "example": ""})
        variables.append({"name": f"{{{{shift_{i}_members}}}}", "desc": sn + " — 值班人员", "category": f"shift_{i}（索引）/ " + sn, "example": ""})
        variables.append({"name": f"{{{{shift_{i}_phones}}}}",  "desc": sn + " — 联系方式", "category": f"shift_{i}（索引）/ " + sn, "example": "138xxx、139xxx"})
        variables.append({"name": f"{{{{shift_{i}_employee_nos}}}}", "desc": sn + " — 工号", "category": f"shift_{i}（索引）/ " + sn, "example": "A001、A002"})
        # 名称写法（等效别名）
        variables.append({"name": f"{{{{{sn}_name}}}}",    "desc": f"↑ 等效于 shift_{i}_name",    "category": f"shift_{i}（索引）/ " + sn, "example": sn})
        variables.append({"name": f"{{{{{sn}_time}}}}",    "desc": f"↑ 等效于 shift_{i}_time",    "category": f"shift_{i}（索引）/ " + sn, "example": "08:30-19:00"})
        variables.append({"name": f"{{{{{sn}_leader}}}}",  "desc": f"↑ 等效于 shift_{i}_leader",  "category": f"shift_{i}（索引）/ " + sn, "example": ""})
        variables.append({"name": f"{{{{{sn}_members}}}}", "desc": f"↑ 等效于 shift_{i}_members", "category": f"shift_{i}（索引）/ " + sn, "example": ""})
        variables.append({"name": f"{{{{{sn}_phones}}}}",  "desc": f"↑ 等效于 shift_{i}_phones",  "category": f"shift_{i}（索引）/ " + sn, "example": "138xxx、139xxx"})
        variables.append({"name": f"{{{{{sn}_employee_nos}}}}", "desc": f"↑ 等效于 shift_{i}_employee_nos", "category": f"shift_{i}（索引）/ " + sn, "example": "A001、A002"})
    return {"variables": variables, "shift_names": shift_names}


@router.get("/templates/default/download", summary="下载默认模板文件")
async def download_default_template(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """下载系统默认模板 .xlsx，用户可在此基础上修改后上传为自定义模板"""
    buf = await ExportService.generate_default_template(db)
    filename = "排班表模板.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/templates", summary="获取导出模板列表")
async def list_export_templates(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    templates = await ExportService.list_templates(db)
    return {"templates": templates}


@router.post("/templates/upload", summary="上传自定义导出模板(.xlsx)")
async def upload_template_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    is_default: bool = Form(False),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "create")),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "仅支持 .xlsx 格式")
    data = await file.read()
    try:
        t = await ExportService.create_template(db, name, data, is_default, description)
        return {"id": t.id, "name": t.name, "is_default": t.is_default}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/templates/{template_id}", summary="删除导出模板")
async def delete_export_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "delete")),
):
    try:
        await ExportService.delete_template(db, template_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/templates/{template_id}/set-default", summary="设为默认模板")
async def set_default_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_permissions("export", "update")),
):
    try:
        await ExportService.set_default_template(db, template_id)
        return {"message": "设置成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
