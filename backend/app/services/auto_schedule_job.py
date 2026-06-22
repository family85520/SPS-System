"""
每月最后一天自动生成下月排班表。
配置项（SysConfig）：
  auto_schedule_enabled  — "true"/"false"
  auto_schedule_hour     — 触发小时 0-23（默认 23）
  auto_schedule_status   — "draft"（默认） / "published"
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select as sa_select

logger = logging.getLogger("auto_schedule")


async def _generate_for_org(db, org_id: int, target_month: date, shift_ids=None, skip_existing=False):
    from app.models.shift_template import SchShiftTemplate
    from app.models.staff import OrgStaff
    from app.models.schedule import SchSchedule
    from app.services.schedule_service import ScheduleService

    if target_month.month == 12:
        next_month = date(target_month.year + 1, 1, 1)
    else:
        next_month = date(target_month.year, target_month.month + 1, 1)
    # 计算 next_month 的最后一天（不是 next_month 的前一天）
    if next_month.month == 12:
        last_day = date(next_month.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(next_month.year, next_month.month + 1, 1) - timedelta(days=1)
    start = next_month
    end = last_day

    if skip_existing:
        existing = (await db.execute(
            sa_select(SchSchedule.id).where(
                SchSchedule.org_id == org_id,
                SchSchedule.date >= start,
                SchSchedule.date <= end,
            ).limit(1)
        )).scalars().first()
        if existing:
            logger.info(f"组织 {org_id} 下月已有排班数据，跳过")
            return None

    shift_query = sa_select(SchShiftTemplate).where(
        SchShiftTemplate.status == 1,
        (SchShiftTemplate.org_id == org_id) | (SchShiftTemplate.org_id.is_(None)),
    )
    if shift_ids:
        shift_query = shift_query.where(SchShiftTemplate.id.in_(shift_ids))
    shifts = (await db.execute(shift_query)).scalars().all()
    if not shifts:
        logger.warning(f"组织 {org_id} 无可用班次模板，跳过")
        return None

    staff_list = (await db.execute(
        sa_select(OrgStaff).where(OrgStaff.org_id == org_id, OrgStaff.status == 1)
    )).scalars().all()
    if not staff_list:
        logger.warning(f"组织 {org_id} 无在岗人员，跳过")
        return None

    s_ids = [s.id for s in shifts]
    staff_ids = [s.id for s in staff_list]

    try:
        result = await ScheduleService.auto_generate(
            db=db,
            start_date=start,
            end_date=end,
            org_id=org_id,
            shift_template_ids=s_ids,
            staff_ids=staff_ids,
            current_user_id=1,
        )
        logger.info(
            f"组织 {org_id} 自动排班完成："
            f"{start}~{end}，"
            f"共 {result.get('report', {}).get('total_shifts', 0)} 条"
        )

        from app.models.audit_log import SysConfig
        status_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_status")
        )).scalars().first()
        if status_cfg and status_cfg.config_value == "published":
            schedule_ids = [s.id for s in result.get("schedules", [])]
            if schedule_ids:
                await ScheduleService.publish(db, schedule_ids, user_id=1)
                logger.info(f"组织 {org_id} 已自动发布 {len(schedule_ids)} 条排班")

        return result
    except Exception as e:
        logger.error(f"组织 {org_id} 自动排班失败: {e}")
        return None


async def run_monthly_auto_schedule(db_factory):
    from app.models.audit_log import SysConfig
    from app.models.organization import OrgOrganization
    from datetime import datetime

    async with db_factory() as db:
        enabled_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_enabled")
        )).scalars().first()
        if not enabled_cfg or enabled_cfg.config_value != "true":
            return

        today = date.today()
        tomorrow = today + timedelta(days=1)
        if today.month == tomorrow.month:
            return

        time_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_time")
        )).scalars().first()
        expected_time = time_cfg.config_value if time_cfg else "23:00"
        try:
            expected_h, expected_m = map(int, expected_time.split(":"))
            now = datetime.now()
            if now.hour != expected_h or now.minute < expected_m or now.minute >= expected_m + 30:
                return
        except (ValueError, TypeError):
            pass

        logger.info(f"开始自动生成下月排班（{today} {expected_time}）")

        org_ids_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_org_ids")
        )).scalars().first()
        org_ids = [int(x.strip()) for x in org_ids_cfg.config_value.split(",") if x.strip()] if (org_ids_cfg and org_ids_cfg.config_value) else None

        shift_ids_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_shift_ids")
        )).scalars().first()
        shift_ids = [int(x.strip()) for x in shift_ids_cfg.config_value.split(",") if x.strip()] if (shift_ids_cfg and shift_ids_cfg.config_value) else None

        skip_cfg = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_skip_existing")
        )).scalars().first()
        skip_existing = skip_cfg.config_value == "true" if skip_cfg else False

        org_query = sa_select(OrgOrganization).where(OrgOrganization.status == 1)
        if org_ids:
            org_query = org_query.where(OrgOrganization.id.in_(org_ids))
        orgs = (await db.execute(org_query)).scalars().all()

        for org in orgs:
            try:
                await _generate_for_org(db, org.id, today, shift_ids, skip_existing)
            except Exception as e:
                logger.error(f"组织 {org.name}({org.id}) 自动排班异常: {e}")

        now_str = today.isoformat()
        last_run = (await db.execute(
            sa_select(SysConfig).where(SysConfig.config_key == "auto_schedule_last_run")
        )).scalars().first()
        if last_run:
            last_run.config_value = now_str
        else:
            db.add(SysConfig(config_key="auto_schedule_last_run", config_value=now_str))
        await db.commit()

        logger.info("自动排班执行完毕")
