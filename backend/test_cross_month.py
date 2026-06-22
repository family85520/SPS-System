"""
测试跨月排班（6、7、8月）是否遵循排班规则
用法：python test_cross_month.py
"""
import asyncio
from datetime import date
from app.database import async_session_factory
from app.services.auto_schedule_job import _generate_for_org
from app.models.organization import OrgOrganization
from app.models.staff import OrgStaff
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate
from sqlalchemy import select as sa_select


async def test_month(db, org_id, target_month, month_name):
    """测试单月排班"""
    print(f"\n{'='*60}")
    print(f"测试 {month_name} 排班...")
    print(f"{'='*60}")

    try:
        result = await _generate_for_org(db, org_id, target_month)
        if not result:
            print(f"  {month_name}：跳过（返回 None）")
            return None

        # 提交事务以保存排班结果
        await db.commit()

        report = result.get('report', {})
        conflicts = result.get('conflicts', [])
        diagnostics = result.get('diagnostics', [])

        print(f"  总班次：{report.get('total_shifts', 0)}")
        print(f"  总人数：{report.get('total_staff', 0)}")
        print(f"  平均工时：{report.get('avg_hours_per_person', 0)} 小时/人")

        if conflicts:
            print(f"\n  冲突 ({len(conflicts)}):")
            for c in conflicts[:5]:
                print(f"    - {c}")
            if len(conflicts) > 5:
                print(f"    ... 还有 {len(conflicts)-5} 个冲突")

        if diagnostics:
            print(f"\n  诊断信息:")
            for d in diagnostics[:3]:
                print(f"    - {d}")

        return result
    except Exception as e:
        print(f"  {month_name}：异常 - {e}")
        import traceback
        traceback.print_exc()
        return None


async def check_special_group_continuity(db, org_id, months):
    """检查特殊人员组跨月连续性"""
    print(f"\n{'='*60}")
    print("检查特殊人员组跨月连续性...")
    print(f"{'='*60}")

    for month_start, month_name in months:
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1)

        schedules = list((await db.execute(
            sa_select(SchSchedule).where(
                SchSchedule.org_id == org_id,
                SchSchedule.date >= month_start,
                SchSchedule.date < month_end,
            )
        )).scalars().all())

        if not schedules:
            print(f"\n  {month_name}：无排班数据")
            continue

        schedule_ids = [s.id for s in schedules]
        details = list((await db.execute(
            sa_select(SchScheduleDetail).where(SchScheduleDetail.schedule_id.in_(schedule_ids))
        )).scalars().all())

        # 统计每人排班次数
        staff_count = {}
        for d in details:
            staff_count[d.staff_id] = staff_count.get(d.staff_id, 0) + 1

        print(f"\n  {month_name} 排班分布:")
        for staff_id, count in sorted(staff_count.items(), key=lambda x: -x[1])[:10]:
            print(f"    员工 {staff_id}: {count} 次")


async def main():
    # 修改月份为目标测试月
    # _generate_for_org 生成下月排班：5月→6月，6月→7月，7月→8月
    months = [
        (date(2026, 5, 1), "6月"),
        (date(2026, 6, 1), "7月"),
        (date(2026, 7, 1), "8月"),
    ]

    async with async_session_factory() as db:
        orgs = (await db.execute(
            sa_select(OrgOrganization).where(OrgOrganization.status == 1)
        )).scalars().all()

        if not orgs:
            print("无可用组织")
            return

        # 选择有人员的组织
        org_id = None
        for org in orgs:
            staff = (await db.execute(
                sa_select(OrgStaff).where(OrgStaff.org_id == org.id, OrgStaff.status == 1)
            )).scalars().all()
            if len(staff) >= 12:  # 至少需要12人
                org_id = org.id
                print(f"测试组织：{org.name} (ID: {org_id}, 人员: {len(staff)})")
                break

        if not org_id:
            print("无可用组织（需要至少12人）")
            return

        # 逐月生成排班
        results = {}
        for month_start, month_name in months:
            result = await test_month(db, org_id, month_start, month_name)
            results[month_name] = result

        # 检查特殊人员组连续性
        await check_special_group_continuity(db, org_id, months)

        # 总结
        print(f"\n{'='*60}")
        print("测试总结")
        print(f"{'='*60}")
        for month_name, result in results.items():
            if result:
                shifts = result.get('report', {}).get('total_shifts', 0)
                conflicts = len(result.get('conflicts', []))
                print(f"  {month_name}: {shifts} 班次, {conflicts} 冲突")
            else:
                print(f"  {month_name}: 跳过")


if __name__ == "__main__":
    asyncio.run(main())
