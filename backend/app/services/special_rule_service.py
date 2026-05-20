from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models import SchSpecialRule, OrgStaff


class SpecialRuleService:
    """特殊排班规则服务"""

    @staticmethod
    async def list_rules(
        db: AsyncSession,
        staff_id: Optional[int] = None,
    ):
        """获取特殊规则列表"""
        stmt = select(SchSpecialRule).order_by(SchSpecialRule.id.desc())
        if staff_id is not None:
            stmt = stmt.where(SchSpecialRule.staff_id == staff_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_rule(db: AsyncSession, rule_id: int) -> Optional[SchSpecialRule]:
        """获取单个特殊规则"""
        stmt = select(SchSpecialRule).where(SchSpecialRule.id == rule_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_rule(db: AsyncSession, data: dict) -> SchSpecialRule:
        """创建特殊规则"""
        staff_stmt = select(OrgStaff.id).where(OrgStaff.id == data["staff_id"]).limit(1)
        staff_result = await db.execute(staff_stmt)
        if not staff_result.first():
            raise ValueError("关联人员不存在")

        rule = SchSpecialRule(
            staff_id=data["staff_id"],
            rule_type=data["rule_type"],
            params=data.get("params", {}),
            effective_from=data.get("effective_from"),
            effective_to=data.get("effective_to"),
            reason=data.get("reason"),
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def update_rule(db: AsyncSession, rule_id: int, data: dict) -> SchSpecialRule:
        """更新特殊规则"""
        rule = await SpecialRuleService.get_rule(db, rule_id)
        if not rule:
            raise ValueError("特殊规则不存在")

        for field, value in data.items():
            if value is not None:
                setattr(rule, field, value)

        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, rule_id: int):
        """删除特殊规则"""
        rule = await SpecialRuleService.get_rule(db, rule_id)
        if not rule:
            raise ValueError("特殊规则不存在")

        await db.delete(rule)
        await db.commit()
