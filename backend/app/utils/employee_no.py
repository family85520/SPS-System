"""工号 / 部门代码 自动生成工具"""

from __future__ import annotations

import re
from datetime import date

from pypinyin import pinyin, Style
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrgStaff, OrgOrganization


def chinese_to_abbreviation(chinese_name: str) -> str:
    """将中文名称转为拼音首字母简称"""
    # 去掉括号、空格等特殊字符
    clean = re.sub(r'[\s\(\)$$（）\[\]【】]', '', chinese_name)
    result = ''
    for py in pinyin(clean, style=Style.FIRST_LETTER):
        if py and py[0]:
            result += py[0].lower()
    return result or 'org'


async def generate_org_code(db: AsyncSession, org_name: str) -> str:
    """根据部门名称生成唯一部门代码（拼音首字母，重复时加数字后缀）"""
    base = chinese_to_abbreviation(org_name)

    # 查询所有已存在的部门代码
    rows = (await db.execute(
        select(OrgOrganization.code).where(OrgOrganization.code.isnot(None))
    )).scalars().all()
    used_codes: set[str] = {c for c in rows if c}

    if base not in used_codes:
        return base

    counter = 2
    while f"{base}{counter}" in used_codes:
        counter += 1
    return f"{base}{counter}"


async def generate_employee_no(db: AsyncSession, org_id: int) -> str:
    """生成下一个工号：{org_code}_{YYYYMM}{三位序号}

    优先使用组织存储的 code 字段，无 code 时从名称实时计算。
    """
    org = (await db.execute(
        select(OrgOrganization).where(OrgOrganization.id == org_id)
    )).scalars().first()

    # 优先用存储的 code，兜底用名称拼音
    if org and org.code:
        abbr = org.code
    elif org:
        abbr = chinese_to_abbreviation(org.name)
    else:
        abbr = 'org'

    today = date.today()
    year_month = f"{today.year}{today.month:02d}"
    prefix = f"{abbr}_{year_month}"

    # 查询当前组织在该月份已有的最大序号
    like_pattern = f"{prefix}%"
    rows = (await db.execute(
        select(OrgStaff.employee_no)
        .where(OrgStaff.employee_no.like(like_pattern))
        .where(OrgStaff.org_id == org_id)
    )).scalars().all()

    max_seq = 0
    pattern = re.compile(rf'^{re.escape(prefix)}(\d{{3}})$')
    for eno in rows:
        m = pattern.match(eno or '')
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq

    next_seq = max_seq + 1
    return f"{prefix}{next_seq:03d}"
