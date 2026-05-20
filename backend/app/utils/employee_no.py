"""工号自动生成工具"""

from __future__ import annotations

import re
from datetime import date

from pypinyin import pinyin, Style
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrgStaff, OrgOrganization


def chinese_to_abbreviation(chinese_name: str) -> str:
    """将中文组织名转为拼音首字母简称"""
    # 去掉括号、空格等特殊字符
    clean = re.sub(r'[\s\(\)（）\[\]【】]', '', chinese_name)
    result = ''
    for py in pinyin(clean, style=Style.FIRST_LETTER):
        if py and py[0]:
            result += py[0].lower()
    return result or 'org'


async def get_unique_org_abbreviation(db: AsyncSession, org_id: int) -> str:
    """获取组织唯一简称（重复时加数字后缀）"""
    # 获取该组织名称
    org = (await db.execute(
        select(OrgOrganization).where(OrgOrganization.id == org_id)
    )).scalars().first()
    if not org:
        return 'org'

    base_abbr = chinese_to_abbreviation(org.name)

    # 查询所有已存在的工号前缀，收集已使用的简称
    rows = (await db.execute(
        select(OrgStaff.employee_no).where(OrgStaff.employee_no.like(f"%_%"))
    )).scalars().all()

    used_abbrs: set[str] = set()
    for eno in rows:
        # 提取 _ 前面的简称部分
        match = re.match(r'^([a-z]+\d*)_\d{11,}', eno or '')
        if match:
            used_abbrs.add(match.group(1))

    if base_abbr not in used_abbrs:
        return base_abbr

    # 有重复，加数字后缀
    counter = 2
    while f"{base_abbr}{counter}" in used_abbrs:
        counter += 1
    return f"{base_abbr}{counter}"


async def generate_employee_no(db: AsyncSession, org_id: int) -> str:
    """生成下一个工号：{org_abbr}_{YYYYMM}{三位序号}"""
    abbr = await get_unique_org_abbreviation(db, org_id)

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
