"""导出服务 - Excel / PDF 生成"""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrgStaff
from app.models.organization import OrgOrganization
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate


# ==================== 工具函数 ====================

def _calc_duration(start_time: str, end_time: str) -> float:
    """计算班次时长（小时），跨夜班特殊处理"""
    try:
        sh, sm = map(int, start_time.split(":"))
        eh, em = map(int, end_time.split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        diff = end_min - start_min
        if diff <= 0:
            diff += 24 * 60
        return round(diff / 60, 1)
    except (ValueError, AttributeError):
        return 0.0


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
STATUS_MAP = {0: "草稿", 1: "已发布", 2: "已撤回", 3: "待审核"}


# ==================== 数据查询 ====================

async def _query_schedule_rows(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    org_id: Optional[int] = None,
) -> list[dict]:
    """查询排班数据，返回按组织/日期排列的行数据"""
    # 查排班记录
    query = (
        select(SchSchedule)
        .where(SchSchedule.date >= start_date, SchSchedule.date <= end_date, SchSchedule.status == 1)
        .order_by(SchSchedule.date, SchSchedule.shift_id)
    )
    if org_id is not None:
        query = query.where(SchSchedule.org_id == org_id)

    schedules = list((await db.execute(query)).scalars().all())
    if not schedules:
        return []

    # 查明细
    schedule_ids = [s.id for s in schedules]
    details = list((await db.execute(
        select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
    )).scalars().all())

    detail_map: dict[int, list[SchScheduleDetail]] = defaultdict(list)
    for d in details:
        detail_map[d.schedule_id].append(d)

    # 班次模板
    shift_ids = list({s.shift_id for s in schedules})
    shift_map = {
        s.id: s for s in (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_ids))
        )).scalars().all()
    }

    # 人员信息
    staff_ids = list({d.staff_id for d in details})
    staff_rows = (await db.execute(
        select(OrgStaff.id, OrgStaff.name, OrgStaff.employee_no, OrgStaff.tags, OrgStaff.org_id)
        .where(OrgStaff.id.in_(staff_ids))
    )).all()
    staff_info: dict[int, dict] = {}
    for row in staff_rows:
        staff_info[row[0]] = {
            "name": row[1], "employee_no": row[2] or "",
            "tags": row[3] if isinstance(row[3], list) else [],
            "org_id": row[4],
        }

    # 组织名称
    org_ids = list({s.org_id for s in schedules})
    org_map = {
        row[0]: row[1] for row in (await db.execute(
            select(OrgOrganization.id, OrgOrganization.name).where(OrgOrganization.id.in_(org_ids))
        )).all()
    }

    # 组装行数据
    rows = []
    for s in schedules:
        shift = shift_map.get(s.shift_id)
        if not shift:
            continue

        day_details = detail_map.get(s.id, [])
        leader_names, member_names = [], []

        for d in day_details:
            info = staff_info.get(d.staff_id, {})
            name = info.get("name", f"ID:{d.staff_id}")
            tags = info.get("tags", [])
            is_leader = getattr(d, "is_leader", False) or (
                isinstance(tags, list) and "带班领导" in tags
            )
            (leader_names if is_leader else member_names).append(name)

        rows.append({
            "date": str(s.date),
            "weekday": WEEKDAY_NAMES[s.date.isoweekday() - 1],
            "org_name": org_map.get(s.org_id, ""),
            "shift_name": shift.name,
            "time_range": f"{shift.start_time}-{shift.end_time}",
            "leader": "、".join(leader_names) if leader_names else "-",
            "members": "、".join(member_names) if member_names else "-",
            "status": STATUS_MAP.get(s.status, "未知"),
            "staff_details": [
                {
                    "staff_id": d.staff_id,
                    "name": staff_info.get(d.staff_id, {}).get("name", ""),
                    "employee_no": staff_info.get(d.staff_id, {}).get("employee_no", ""),
                    "org_id": staff_info.get(d.staff_id, {}).get("org_id"),
                    "org_name": org_map.get(staff_info.get(d.staff_id, {}).get("org_id", 0), ""),
                    "shift_name": shift.name,
                    "date": str(s.date),
                    "duration": _calc_duration(shift.start_time, shift.end_time),
                }
                for d in day_details
            ],
        })

    return rows


# ==================== Excel 生成 ====================

def _build_org_excel(rows: list[dict]) -> io.BytesIO:
    """按组织维度生成排班表 Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "排班表"

    # 样式
    hdr_font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    hdr_fill = PatternFill(start_color="0A63D8", end_color="0A63D8", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    cell_font = Font(size=10)
    center = Alignment(horizontal="center", vertical="center")
    left_wrap = Alignment(vertical="center", wrap_text=True)

    thin = Border(
        left=Side(style="thin", color="E6EAF0"),
        right=Side(style="thin", color="E6EAF0"),
        top=Side(style="thin", color="E6EAF0"),
        bottom=Side(style="thin", color="E6EAF0"),
    )
    even_fill = PatternFill(start_color="F5F7FA", end_color="F5F7FA", fill_type="solid")

    # 表头
    headers = ["日期", "星期", "组织", "班次", "起止时间", "值班领导", "值班人员", "状态"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, thin

    # 数据行
    for ri, rd in enumerate(rows, 2):
        vals = [rd["date"], rd["weekday"], rd["org_name"], rd["shift_name"],
                rd["time_range"], rd["leader"], rd["members"], rd["status"]]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            c.font, c.border = cell_font, thin
            c.alignment = center if ci in (1, 2, 4, 5, 8) else left_wrap
            if ri % 2 == 0:
                c.fill = even_fill

    # 列宽
    widths = [14, 8, 16, 10, 16, 20, 42, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _build_person_excel(rows: list[dict], start_date: date, end_date: date) -> io.BytesIO:
    """按人员维度生成排班表 Excel（透视表）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # 构建人员维度数据
    staff_map: dict[int, dict] = {}
    for row in rows:
        for sd in row.get("staff_details", []):
            sid = sd["staff_id"]
            if sid not in staff_map:
                staff_map[sid] = {
                    "name": sd["name"],
                    "employee_no": sd["employee_no"],
                    "org_name": sd["org_name"],
                    "dates": {},
                    "total_shifts": 0,
                    "total_hours": 0.0,
                }
            s = staff_map[sid]
            s["dates"][sd["date"]] = sd["shift_name"]
            s["total_shifts"] += 1
            s["total_hours"] += sd["duration"]

    # 生成日期列
    date_cols = []
    cur = start_date
    while cur <= end_date:
        date_cols.append({"date": str(cur), "label": f"{cur.month}/{cur.day}({WEEKDAY_NAMES[cur.isoweekday()-1]})"})
        cur += timedelta(days=1)

    # 排序
    staff_list = sorted(staff_map.values(), key=lambda x: x["name"])

    wb = Workbook()
    ws = wb.active
    ws.title = "按人员排班"

    # 样式
    hdr_font = Font(name="微软雅黑", bold=True, size=10, color="FFFFFF")
    hdr_fill = PatternFill(start_color="0A63D8", end_color="0A63D8", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_font = Font(size=9)
    center = Alignment(horizontal="center", vertical="center")
    thin = Border(
        left=Side(style="thin", color="E6EAF0"),
        right=Side(style="thin", color="E6EAF0"),
        top=Side(style="thin", color="E6EAF0"),
        bottom=Side(style="thin", color="E6EAF0"),
    )
    even_fill = PatternFill(start_color="F5F7FA", end_color="F5F7FA", fill_type="solid")

    # 无班次颜色
    no_shift_fill = PatternFill(start_color="FAFAFA", end_color="FAFAFA", fill_type="solid")

    # 表头
    fixed_headers = ["姓名", "工号", "组织"]
    tail_headers = ["总班次", "总工时(h)"]
    all_headers = fixed_headers + [d["label"] for d in date_cols] + tail_headers
    for col, h in enumerate(all_headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, thin

    # 数据行
    for ri, staff in enumerate(staff_list, 2):
        # 固定列
        ws.cell(row=ri, column=1, value=staff["name"]).font = Font(size=10, bold=True)
        ws.cell(row=ri, column=1, value=staff["name"]).border = thin
        ws.cell(row=ri, column=1, value=staff["name"]).alignment = center

        ws.cell(row=ri, column=2, value=staff["employee_no"]).font = cell_font
        ws.cell(row=ri, column=2, value=staff["employee_no"]).border = thin
        ws.cell(row=ri, column=2, value=staff["employee_no"]).alignment = center

        ws.cell(row=ri, column=3, value=staff["org_name"]).font = cell_font
        ws.cell(row=ri, column=3, value=staff["org_name"]).border = thin

        # 日期列
        for di, dc in enumerate(date_cols):
            col_idx = len(fixed_headers) + di + 1
            shift_name = staff["dates"].get(dc["date"], "")
            c = ws.cell(row=ri, column=col_idx, value=shift_name)
            c.font = cell_font
            c.alignment = center
            c.border = thin
            if shift_name:
                c.fill = PatternFill(start_color="EBF5FF", end_color="EBF5FF", fill_type="solid")
            else:
                c.fill = no_shift_fill

        # 统计列
        tail_start = len(fixed_headers) + len(date_cols) + 1
        ws.cell(row=ri, column=tail_start, value=staff["total_shifts"]).font = cell_font
        ws.cell(row=ri, column=tail_start, value=staff["total_shifts"]).border = thin
        ws.cell(row=ri, column=tail_start, value=staff["total_shifts"]).alignment = center

        ws.cell(row=ri, column=tail_start + 1, value=staff["total_hours"]).font = cell_font
        ws.cell(row=ri, column=tail_start + 1, value=staff["total_hours"]).border = thin
        ws.cell(row=ri, column=tail_start + 1, value=staff["total_hours"]).alignment = center

        if ri % 2 == 0:
            for ci in range(1, len(all_headers) + 1):
                cell = ws.cell(row=ri, column=ci)
                if not cell.fill or cell.fill.start_color.index in ("00000000", "FAFAFA", "EBF5FF"):
                    cell.fill = even_fill

    # 列宽
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 16
    for i in range(len(date_cols)):
        ws.column_dimensions[get_column_letter(len(fixed_headers) + i + 1)].width = 10
    ws.column_dimensions[get_column_letter(tail_start)].width = 10
    ws.column_dimensions[get_column_letter(tail_start + 1)].width = 12

    ws.freeze_panes = "D2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ==================== 统计报表 Excel ====================

async def _build_statistics_excel(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    org_id: Optional[int] = None,
) -> io.BytesIO:
    """生成统计报表 Excel"""
    from app.services.schedule_service import ScheduleService

    stats = await ScheduleService.get_statistics(db, start_date=start_date, end_date=end_date, org_id=org_id)
    items = stats.get("items", [])
    summary = stats.get("summary", {})

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "排班统计"

    # 样式
    hdr_font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    hdr_fill = PatternFill(start_color="0A63D8", end_color="0A63D8", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_font = Font(size=10)
    center = Alignment(horizontal="center", vertical="center")
    thin = Border(
        left=Side(style="thin", color="E6EAF0"),
        right=Side(style="thin", color="E6EAF0"),
        top=Side(style="thin", color="E6EAF0"),
        bottom=Side(style="thin", color="E6EAF0"),
    )
    even_fill = PatternFill(start_color="F5F7FA", end_color="F5F7FA", fill_type="solid")
    gold_font = Font(size=10, bold=True, color="D4A017")

    # 汇总区域
    summary_items = [
        ("参与人数", summary.get("total_staff", 0)),
        ("总班次数", summary.get("total_shifts", 0)),
        ("人均班次", summary.get("avg_shifts_per_person", 0)),
        ("人均工时(h)", summary.get("avg_hours_per_person", 0)),
        ("总夜班数", summary.get("total_night_shifts", 0)),
        ("节假日班数", summary.get("total_holiday_shifts", 0)),
    ]
    for i, (label, val) in enumerate(summary_items):
        col = i * 2 + 1
        ws.cell(row=1, column=col, value=label).font = Font(size=9, color="556173")
        ws.cell(row=1, column=col).alignment = center
        ws.cell(row=1, column=col + 1, value=val).font = Font(size=14, bold=True, color="0A63D8")
        ws.cell(row=1, column=col + 1).alignment = center

    # 表头
    headers = ["排名", "姓名", "工号", "组织", "排班天数", "总工时(h)", "夜班数", "周末班数", "节假日班数", "领导班数", "权重分"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=3, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, thin

    # 数据
    for ri, item in enumerate(items, 4):
        rank = ri - 3
        vals = [
            rank,
            item.get("staff_name", ""),
            item.get("employee_no", ""),
            item.get("org_name", ""),
            item.get("total_shifts", 0),
            item.get("total_hours", 0),
            item.get("night_shifts", 0),
            item.get("weekend_shifts", 0),
            item.get("holiday_shifts", 0),
            item.get("leader_shifts", 0),
            item.get("weight_score", 0),
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            c.font = gold_font if rank <= 3 else cell_font
            c.border = thin
            c.alignment = center
            if ri % 2 == 0:
                c.fill = even_fill

    # 列宽
    widths = [6, 12, 12, 16, 10, 12, 10, 10, 12, 10, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A4"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


async def _build_statistics_pdf(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    org_id: Optional[int] = None,
) -> io.BytesIO:
    """生成统计报表 PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    from app.services.schedule_service import ScheduleService

    stats = await ScheduleService.get_statistics(db, start_date=start_date, end_date=end_date, org_id=org_id)
    items = stats.get("items", [])
    summary = stats.get("summary", {})

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        cn_font = "STSong-Light"
    except Exception:
        cn_font = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    body_size = 9
    body_leading = 12

    # 样式
    style_title = ParagraphStyle("T", fontName=cn_font, fontSize=18, alignment=1, spaceAfter=3 * mm)
    style_sub = ParagraphStyle("S", fontName=cn_font, fontSize=10, alignment=1, spaceAfter=5 * mm)
    style_hdr = ParagraphStyle("H", fontName=cn_font, fontSize=body_size, leading=body_leading, alignment=1)
    style_cell = ParagraphStyle("C", fontName=cn_font, fontSize=body_size, leading=body_leading, alignment=1)
    style_cell_left = ParagraphStyle("CL", fontName=cn_font, fontSize=body_size, leading=body_leading)
    style_summary_label = ParagraphStyle("SL", fontName=cn_font, fontSize=9, alignment=1, textColor=colors.HexColor("#556173"))
    style_summary_val = ParagraphStyle("SV", fontName=cn_font, fontSize=14, leading=18, alignment=1, textColor=colors.HexColor("#0A63D8"))
    style_footer = ParagraphStyle("F", fontName=cn_font, fontSize=10, spaceAfter=3 * mm)

    elements = []

    # 标题
    elements.append(Paragraph(f"{start_date.year}年{start_date.month}月 排班统计报表", style_title))
    elements.append(Paragraph(f"统计周期：{start_date} 至 {end_date}", style_sub))

    # 汇总行
    summary_items = [
        ("参与人数", str(summary.get("total_staff", 0))),
        ("总班次数", str(summary.get("total_shifts", 0))),
        ("人均班次", str(summary.get("avg_shifts_per_person", 0))),
        ("人均工时", f"{summary.get('avg_hours_per_person', 0)}h"),
        ("总夜班数", str(summary.get("total_night_shifts", 0))),
        ("节假日班", str(summary.get("total_holiday_shifts", 0))),
    ]
    sum_label_row = [Paragraph(l, style_summary_label) for l, _ in summary_items]
    sum_val_row = [Paragraph(v, style_summary_val) for _, v in summary_items]

    sum_table = Table([sum_label_row, sum_val_row], colWidths=[28 * mm] * 6)
    sum_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 8 * mm))

    # 明细表头
    headers = ["排名", "姓名", "工号", "组织", "排班天数", "总工时(h)", "夜班", "周末班", "节假日", "领导班", "权重分"]
    table_data = [[Paragraph(h, style_hdr) for h in headers]]

    # 明细数据（用纯文本避免 CID 字体不支持 emoji）
    rank_colors = {1: "#D4A017", 2: "#A8A8A8", 3: "#CD7F32"}
    rank_symbols = {1: "★", 2: "★", 3: "★"}
    style_rank = ParagraphStyle("RC", fontName=cn_font, fontSize=body_size, leading=body_leading, alignment=1)
    for idx, item in enumerate(items):
        rank = idx + 1
        rank_str = str(rank)
        if rank in rank_symbols:
            rank_str = f"{rank_symbols[rank]} {rank}"

        rank_para = Paragraph(rank_str, style_cell)
        if rank in rank_colors:
            rank_para = Paragraph(
                f'<font color="{rank_colors[rank]}"><b>{rank_str}</b></font>',
                style_rank,
            )

        row = [
            rank_para,
            Paragraph(item.get("staff_name", ""), style_cell),
            Paragraph(item.get("employee_no", ""), style_cell),
            Paragraph(item.get("org_name", ""), style_cell_left),
            Paragraph(str(item.get("total_shifts", 0)), style_cell),
            Paragraph(f'{item.get("total_hours", 0):.1f}', style_cell),
            Paragraph(str(item.get("night_shifts", 0)), style_cell),
            Paragraph(str(item.get("weekend_shifts", 0)), style_cell),
            Paragraph(str(item.get("holiday_shifts", 0)), style_cell),
            Paragraph(str(item.get("leader_shifts", 0)), style_cell),
            Paragraph(f'{item.get("weight_score", 0):.1f}', style_cell),
        ]
        table_data.append(row)

    col_widths = [14 * mm, 16 * mm, 16 * mm, 24 * mm, 14 * mm, 16 * mm, 10 * mm, 12 * mm, 12 * mm, 12 * mm, 16 * mm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), cn_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A63D8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6EAF0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    # 页脚
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph(
        "制定人：________________　　　审批人：________________　　　日期：________________",
        style_footer,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


# ==================== PDF 生成 ====================

def _build_schedule_pdf(
    rows: list[dict],
    start_date: date,
    end_date: date,
    unit_name: str = "",
) -> io.BytesIO:
    """生成排班表 PDF（A4 横向）"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    # 注册中文 CID 字体
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        cn_font = "STSong-Light"
    except Exception:
        cn_font = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # 样式
    style_title = ParagraphStyle("T", fontName=cn_font, fontSize=18, alignment=1, spaceAfter=3 * mm)
    style_sub = ParagraphStyle("S", fontName=cn_font, fontSize=11, alignment=1, spaceAfter=5 * mm)
    style_cell = ParagraphStyle("C", fontName=cn_font, fontSize=8, leading=11)
    style_hdr = ParagraphStyle("H", fontName=cn_font, fontSize=9, leading=12, alignment=1)
    style_footer = ParagraphStyle("F", fontName=cn_font, fontSize=10, spaceAfter=3 * mm)

    elements = []

    # 标题
    title_text = f"{unit_name} " if unit_name else ""
    title_text += f"{start_date.year}年{start_date.month}月 排班表"
    elements.append(Paragraph(title_text, style_title))
    elements.append(Paragraph(f"统计周期：{start_date} 至 {end_date}", style_sub))
    elements.append(Spacer(1, 3 * mm))

    # 表头
    col_names = ["日期", "星期", "组织", "班次", "起止时间", "值班领导", "值班人员", "状态"]
    table_data = [[Paragraph(h, style_hdr) for h in col_names]]

    for rd in rows:
        table_data.append([
            Paragraph(rd["date"], style_cell),
            Paragraph(rd["weekday"], style_cell),
            Paragraph(rd["org_name"], style_cell),
            Paragraph(rd["shift_name"], style_cell),
            Paragraph(rd["time_range"], style_cell),
            Paragraph(rd["leader"], style_cell),
            Paragraph(rd["members"], style_cell),
            Paragraph(rd["status"], style_cell),
        ])

    col_widths = [20 * mm, 12 * mm, 22 * mm, 14 * mm, 20 * mm, 26 * mm, 80 * mm, 14 * mm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), cn_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A63D8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6EAF0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    # 页脚：签章栏
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph(
        "制定人：________________　　　审批人：________________　　　日期：________________",
        style_footer,
    ))
    elements.append(Spacer(1, 8 * mm))
    style_stamp = ParagraphStyle("ST", fontName=cn_font, fontSize=10, alignment=2)
    elements.append(Paragraph("（公章位置）", style_stamp))

    doc.build(elements)
    buf.seek(0)
    return buf


def _build_person_pdf(
    rows: list[dict],
    start_date: date,
    end_date: date,
    unit_name: str = "",
) -> io.BytesIO:
    """生成按人员维度的排班表 PDF（A4 横向）"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        cn_font = "STSong-Light"
    except Exception:
        cn_font = "Helvetica"

    # 构建人员维度数据（与 Excel 逻辑一致）
    staff_map: dict[int, dict] = {}
    for row in rows:
        for sd in row.get("staff_details", []):
            sid = sd["staff_id"]
            if sid not in staff_map:
                staff_map[sid] = {
                    "name": sd["name"],
                    "employee_no": sd["employee_no"],
                    "org_name": sd["org_name"],
                    "dates": {},
                    "total_shifts": 0,
                    "total_hours": 0.0,
                }
            s = staff_map[sid]
            s["dates"][sd["date"]] = sd["shift_name"]
            s["total_shifts"] += 1
            s["total_hours"] += sd["duration"]

    staff_list = sorted(staff_map.values(), key=lambda x: x["name"])

    # 生成日期列
    date_cols = []
    cur = start_date
    while cur <= end_date:
        date_cols.append({
            "date": str(cur),
            "label": f"{cur.month}/{cur.day}",
            "weekday": WEEKDAY_NAMES[cur.isoweekday() - 1],
        })
        cur += timedelta(days=1)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # 字号自适应：日期越多字号越小
    date_count = len(date_cols)
    if date_count <= 15:
        body_size, body_leading = 8, 11
    elif date_count <= 25:
        body_size, body_leading = 7, 9
    else:
        body_size, body_leading = 6, 8

    # 样式
    style_title = ParagraphStyle("T", fontName=cn_font, fontSize=16, alignment=1, spaceAfter=3 * mm)
    style_sub = ParagraphStyle("S", fontName=cn_font, fontSize=10, alignment=1, spaceAfter=5 * mm)
    style_hdr = ParagraphStyle("H", fontName=cn_font, fontSize=body_size, leading=body_leading, alignment=1)
    style_cell = ParagraphStyle("C", fontName=cn_font, fontSize=body_size, leading=body_leading, alignment=1)
    style_footer = ParagraphStyle("F", fontName=cn_font, fontSize=10, spaceAfter=3 * mm)

    elements = []

    # 标题
    title_text = f"{unit_name} " if unit_name else ""
    title_text += f"{start_date.year}年{start_date.month}月 排班表（按人员）"
    elements.append(Paragraph(title_text, style_title))
    elements.append(Paragraph(f"统计周期：{start_date} 至 {end_date}", style_sub))
    elements.append(Spacer(1, 3 * mm))

    # 表头：姓名 | 工号 | 组织 | 日期列... | 总班次 | 总工时
    hdr_row = [
        Paragraph("姓名", style_hdr),
        Paragraph("工号", style_hdr),
        Paragraph("组织", style_hdr),
    ]
    for dc in date_cols:
        hdr_row.append(Paragraph(f"{dc['label']}<br/>{dc['weekday']}", style_hdr))
    hdr_row.append(Paragraph("总班次", style_hdr))
    hdr_row.append(Paragraph("总工时", style_hdr))

    table_data = [hdr_row]

    # 数据行
    for staff in staff_list:
        row = [
            Paragraph(staff["name"], style_cell),
            Paragraph(staff["employee_no"], style_cell),
            Paragraph(staff["org_name"], style_cell),
        ]
        for dc in date_cols:
            shift = staff["dates"].get(dc["date"], "")
            row.append(Paragraph(shift if shift else "-", style_cell))
        row.append(Paragraph(str(staff["total_shifts"]), style_cell))
        row.append(Paragraph(f"{staff['total_hours']:.1f}", style_cell))
        table_data.append(row)

    # 动态列宽计算
    page_w = landscape(A4)[0] - 10 * mm * 2  # 可用页面宽度
    date_count = len(date_cols)

    if date_count <= 15:
        fixed_col_w = [20 * mm, 16 * mm, 22 * mm]
        tail_col_w = [14 * mm, 14 * mm]
        date_col_min = 10 * mm
    elif date_count <= 25:
        fixed_col_w = [16 * mm, 12 * mm, 16 * mm]
        tail_col_w = [10 * mm, 10 * mm]
        date_col_min = 7 * mm
    else:
        fixed_col_w = [14 * mm, 10 * mm, 14 * mm]
        tail_col_w = [8 * mm, 8 * mm]
        date_col_min = 5 * mm

    fixed_sum = sum(fixed_col_w)
    tail_sum = sum(tail_col_w)
    avail_w = page_w - fixed_sum - tail_sum
    date_col_w = max(avail_w / date_count, date_col_min) if date_count else 10 * mm

    col_widths = fixed_col_w
    col_widths += [date_col_w] * date_count
    col_widths += tail_col_w

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), cn_font),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A63D8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6EAF0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(table)

    # 页脚
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph(
        "制定人：________________　　　审批人：________________　　　日期：________________",
        style_footer,
    ))
    elements.append(Spacer(1, 8 * mm))
    style_stamp = ParagraphStyle("ST", fontName=cn_font, fontSize=10, alignment=2)
    elements.append(Paragraph("（公章位置）", style_stamp))

    doc.build(elements)
    buf.seek(0)
    return buf


# ==================== 公开接口 ====================

class ExportService:
    """导出服务统一入口"""

    @staticmethod
    async def schedule_excel(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
        dimension: str = "org",
    ) -> io.BytesIO:
        rows = await _query_schedule_rows(db, start_date, end_date, org_id)
        if not rows:
            raise ValueError("当前筛选条件下无排班数据")

        if dimension == "person":
            return _build_person_excel(rows, start_date, end_date)
        return _build_org_excel(rows)

    @staticmethod
    async def schedule_pdf(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
        unit_name: str = "",
        dimension: str = "org",
    ) -> io.BytesIO:
        rows = await _query_schedule_rows(db, start_date, end_date, org_id)
        if not rows:
            raise ValueError("当前筛选条件下无排班数据")
        if dimension == "person":
            return _build_person_pdf(rows, start_date, end_date, unit_name)
        return _build_schedule_pdf(rows, start_date, end_date, unit_name)

    @staticmethod
    async def statistics_excel(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
    ) -> io.BytesIO:
        from app.services.schedule_service import ScheduleService
        stats = await ScheduleService.get_statistics(db, start_date=start_date, end_date=end_date, org_id=org_id)
        if not stats.get("items"):
            raise ValueError("当前筛选条件下无排班统计数据")
        return await _build_statistics_excel(db, start_date, end_date, org_id)

    @staticmethod
    async def statistics_pdf(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        org_id: Optional[int] = None,
    ) -> io.BytesIO:
        from app.services.schedule_service import ScheduleService
        stats = await ScheduleService.get_statistics(db, start_date=start_date, end_date=end_date, org_id=org_id)
        if not stats.get("items"):
            raise ValueError("当前筛选条件下无排班统计数据")
        return await _build_statistics_pdf(db, start_date, end_date, org_id)
