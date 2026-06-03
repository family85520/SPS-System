from sqlalchemy import select, and_, or_, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models import SchShiftTemplate, SchSchedule
from app.models.duty_team import SchDutyTeam
from app.schemas.shift_template import ShiftTemplateCreate, ShiftTemplateUpdate


class ShiftTemplateService:
    """班次模板服务"""

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        org_id: Optional[int] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ):
        """获取班次模板列表"""
        stmt = select(SchShiftTemplate)

        if org_id is not None:
            stmt = stmt.where(
                or_(
                    SchShiftTemplate.org_id == org_id,
                    SchShiftTemplate.org_id.is_(None),
                )
            )
        if status is not None:
            stmt = stmt.where(SchShiftTemplate.status == status)
        if keyword:
            stmt = stmt.where(SchShiftTemplate.name.ilike(f"%{keyword}%"))

        stmt = stmt.order_by(SchShiftTemplate.id.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_template(db: AsyncSession, template_id: int) -> Optional[SchShiftTemplate]:
        """获取单个班次模板"""
        stmt = select(SchShiftTemplate).where(SchShiftTemplate.id == template_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_template(db: AsyncSession, data: ShiftTemplateCreate) -> SchShiftTemplate:
        """创建班次模板"""
        # 名称唯一性校验
        dup_stmt = select(SchShiftTemplate).where(SchShiftTemplate.name == data.name)
        if data.org_id is not None:
            dup_stmt = dup_stmt.where(
                or_(
                    SchShiftTemplate.org_id == data.org_id,
                    SchShiftTemplate.org_id.is_(None),
                )
            )
        else:
            dup_stmt = dup_stmt.where(SchShiftTemplate.org_id.is_(None))

        dup_result = await db.execute(dup_stmt)
        if dup_result.scalars().first():
            raise ValueError(f"班次名称「{data.name}」已存在，请使用其他名称")

        duration = ShiftTemplateService.calc_duration(data.start_time, data.end_time)

        template = SchShiftTemplate(
            name=data.name,
            org_id=data.org_id,
            start_time=data.start_time,
            end_time=data.end_time,
            duration_hours=duration,
            color=data.color,
            leader_min=data.leader_min,
            leader_max=data.leader_max,
            leader_pool=data.leader_pool,
            leader_enabled=data.leader_enabled,
            leader_rotation_frequency=data.leader_rotation_frequency,
            leader_count=data.leader_count,
            leader_use_tag=data.leader_use_tag,
            leader_tag_name=data.leader_tag_name,
            member_min=data.member_min,
            member_max=data.member_max,
            member_enabled=data.member_enabled,
            member_rotation_frequency=data.member_rotation_frequency,
            apply_days=data.apply_days,
            special_enabled=data.special_enabled,
            special_rotation_frequency=data.special_rotation_frequency,
            special_count=data.special_count,
            special_pool=data.special_pool,
            special_exclude_from_member=data.special_exclude_from_member,
            constraint_ids=data.constraint_ids,
            status=1,
        )

        db.add(template)
        await db.flush()
        await db.refresh(template)
        return template

    @staticmethod
    async def update_template(db: AsyncSession, template_id: int, data: ShiftTemplateUpdate) -> SchShiftTemplate:
        """更新班次模板"""
        template = await ShiftTemplateService.get_template(db, template_id)
        if not template:
            raise ValueError("班次模板不存在")

        update_data = data.model_dump(exclude_unset=True)

        # 名称唯一性校验（排除自身）
        if "name" in update_data and update_data["name"] is not None:
            new_name = update_data["name"]
            dup_stmt = select(SchShiftTemplate).where(
                SchShiftTemplate.name == new_name,
                SchShiftTemplate.id != template_id,
            )
            target_org_id = update_data.get("org_id", template.org_id)
            if target_org_id is not None:
                dup_stmt = dup_stmt.where(
                    or_(
                        SchShiftTemplate.org_id == target_org_id,
                        SchShiftTemplate.org_id.is_(None),
                    )
                )
            else:
                dup_stmt = dup_stmt.where(SchShiftTemplate.org_id.is_(None))
            dup_result = await db.execute(dup_stmt)
            if dup_result.scalars().first():
                raise ValueError(f"班次名称「{new_name}」已存在，请使用其他名称")

        for field, value in update_data.items():
            setattr(template, field, value)

        if "start_time" in update_data or "end_time" in update_data:
            template.duration_hours = ShiftTemplateService.calc_duration(
                template.start_time, template.end_time
            )

        await db.flush()
        await db.refresh(template)
        return template

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int):
        """删除班次模板（含轮换组和值班组）"""
        template = await ShiftTemplateService.get_template(db, template_id)
        if not template:
            raise ValueError("班次模板不存在")

        # 检查是否关联排班记录
        schedule_count = (await db.execute(
            select(func.count()).select_from(SchSchedule).where(SchSchedule.shift_id == template_id)
        )).scalar()
        if schedule_count and schedule_count > 0:
            raise ValueError("该班次模板已关联排班记录，不允许删除，请使用停用功能")

        # 删除关联的值班组
        await db.execute(
            sa_delete(SchDutyTeam).where(SchDutyTeam.shift_template_id == template_id)
        )

        await db.delete(template)
        await db.flush()

    @staticmethod
    async def copy_template(db: AsyncSession, template_id: int) -> SchShiftTemplate:
        """复制班次模板"""
        source = await ShiftTemplateService.get_template(db, template_id)
        if not source:
            raise ValueError("班次模板不存在")

        new_name = f"{source.name}(副本)"

        new_template = SchShiftTemplate(
            name=new_name,
            org_id=source.org_id,
            start_time=source.start_time,
            end_time=source.end_time,
            duration_hours=source.duration_hours,
            color=source.color,
            leader_min=source.leader_min,
            leader_max=source.leader_max,
            leader_pool=source.leader_pool,
            member_min=source.member_min,
            member_max=source.member_max,
            apply_days=source.apply_days,
            status=1,
        )

        db.add(new_template)
        await db.flush()
        await db.refresh(new_template)
        return new_template

    @staticmethod
    async def toggle_status(db: AsyncSession, template_id: int) -> SchShiftTemplate:
        """启用/停用班次模板"""
        template = await ShiftTemplateService.get_template(db, template_id)
        if not template:
            raise ValueError("班次模板不存在")

        template.status = 0 if template.status == 1 else 1
        await db.flush()
        await db.refresh(template)
        return template

    @staticmethod
    def calc_duration(start_time: str, end_time: str) -> float:
        """计算班次时长（小时），支持跨夜班"""
        parts_s = start_time.split(":")
        parts_e = end_time.split(":")
        start_min = int(parts_s[0]) * 60 + int(parts_s[1])
        end_min = int(parts_e[0]) * 60 + int(parts_e[1])

        if end_min <= start_min:
            end_min += 24 * 60

        return round((end_min - start_min) / 60, 1)
