"""
手动触发自动排班（跳过日期校验，用于测试）
用法：python test_auto_schedule.py
"""
import asyncio
from datetime import date
from app.database import async_session_factory
from app.services.auto_schedule_job import _generate_for_org
from app.models.audit_log import SysConfig
from app.models.organization import OrgOrganization
from sqlalchemy import select


async def main():
    # 修改月份为目标测试月
    target_month = date(2026, 6, 1)  # 生成7月排班
    # target_month = date(2026, 7, 1)  # 生成8月排班

    async with async_session_factory() as db:
        orgs = (await db.execute(
            select(OrgOrganization).where(OrgOrganization.status == 1)
        )).scalars().all()

        for org in orgs:
            print(f"正在为组织 [{org.name}] 生成排班...")
            try:
                result = await _generate_for_org(db, org.id, target_month)
                if result:
                    print(f"  完成：共 {result.get('report', {}).get('total_shifts', 0)} 条排班")
                    for msg in result.get('diagnostics', [])[:5]:
                        print(f"  [诊断] {msg}")
                else:
                    print(f"  跳过（已存在或无可用的班次模板）")
            except Exception as e:
                print(f"  失败：{e}")


if __name__ == "__main__":
    asyncio.run(main())
