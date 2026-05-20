from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models import SchConstraint
from app.schemas.constraint import ConstraintCreate, ConstraintUpdate, BatchPriorityRequest


# 预置规则类型定义
PRESET_RULES = [
    # 基础工时约束
    {"rule_type": "MAX_CONTINUOUS_DAYS", "rule_name": "连续工作上限", "params": {"max_days": 5}},
    {"rule_type": "MIN_REST_AFTER_CONTINUOUS", "rule_name": "连续工作后最少休息", "params": {"rest_days": 1}},
    {"rule_type": "MIN_SHIFT_INTERVAL", "rule_name": "班次最少间隔", "params": {"hours": 8}},
    {"rule_type": "MAX_SHIFTS_PER_DAY", "rule_name": "每天最多上班数", "params": {"count": 1}},
    {"rule_type": "MAX_WEEKLY_HOURS", "rule_name": "每周最多工作时长", "params": {"hours": 48}},

    # 夜班约束
    {"rule_type": "MIN_REST_AFTER_NIGHT", "rule_name": "夜班后最少休息", "params": {"hours": 12}},
    {"rule_type": "MAX_CONSECUTIVE_NIGHTS", "rule_name": "连续夜班上限", "params": {"max_days": 3}},
    {"rule_type": "MIN_INTERVAL_BETWEEN_NIGHTS", "rule_name": "夜班之间最少间隔天数", "params": {"days": 2}},
    {"rule_type": "MAX_NIGHTS_PER_MONTH", "rule_name": "每月最多夜班次数", "params": {"count": 8}},

    # 均衡轮转
    {"rule_type": "EQUAL_DISTRIBUTION", "rule_name": "工作量均衡分配", "params": {"enabled": True, "tolerance_days": 2}},
    {"rule_type": "LEADER_ROTATION", "rule_name": "值班领导轮换均衡", "params": {"enabled": True}},
    {"rule_type": "WEEKEND_ROTATION", "rule_name": "周末轮转均衡", "params": {"enabled": True, "min_times_per_month": 2}},

    # 节假日与周末
    {"rule_type": "HOLIDAY_MODE", "rule_name": "节假日排班模式", "params": {"mode": "normal"}},
    {"rule_type": "WEEKEND_DIFF", "rule_name": "周末差异化", "params": {"enabled": False}},

    # 特殊约束
    {"rule_type": "NEW_STAFF_PAIRING", "rule_name": "新员工必须搭配老员工", "params": {"enabled": True}},
]

PRESET_RULE_TYPES = {r["rule_type"] for r in PRESET_RULES}

class ConstraintService:
    """约束规则服务"""

    @staticmethod
    async def init_preset_rules(db: AsyncSession):
        """初始化预置规则（启动时调用）"""
        for idx, rule in enumerate(PRESET_RULES):
            stmt = select(SchConstraint).where(SchConstraint.rule_type == rule["rule_type"])
            result = await db.execute(stmt)
            existing = result.scalars().first()
            if not existing:
                db.add(SchConstraint(
                    rule_type=rule["rule_type"],
                    rule_name=rule["rule_name"],
                    params=rule["params"],
                    priority=idx + 1,
                    scope_type="all",
                    enabled=True,
                    is_preset=True,
                ))
        await db.commit()

    @staticmethod
    async def list_constraints(
        db: AsyncSession,
        enabled: Optional[bool] = None,
    ):
        """获取约束规则列表"""
        stmt = select(SchConstraint).order_by(SchConstraint.priority.asc(), SchConstraint.id.asc())
        if enabled is not None:
            stmt = stmt.where(SchConstraint.enabled == enabled)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_constraint(db: AsyncSession, constraint_id: int) -> Optional[SchConstraint]:
        """获取单个约束规则"""
        stmt = select(SchConstraint).where(SchConstraint.id == constraint_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_constraint(db: AsyncSession, data: ConstraintCreate) -> SchConstraint:
        """创建自定义约束规则"""
        # 校验：同类型 + 同适用范围不能重复
        dup_stmt = select(SchConstraint).where(
            SchConstraint.rule_type == data.rule_type,
            SchConstraint.scope_type == data.scope_type
        )
        if data.scope_type == "all":
            # 全局范围内同类型只能有一条
            dup_stmt = dup_stmt.where(SchConstraint.scope_type == "all")
        elif data.scope_type == "org" and data.scope_ids:
            # 机构范围内同类型 + 同机构ID不能重复
            dup_stmt = dup_stmt.where(SchConstraint.scope_type == "org")
            
        dup_result = await db.execute(dup_stmt)
        existing_list = dup_result.scalars().all()

        for existing in existing_list:
            if data.scope_type == "all":
                raise ValueError(f"全局范围内已存在「{data.rule_name}」类型的规则（ID: {existing.id}），请修改已有规则的参数")
            if data.scope_type == "org" and existing.scope_ids:
                overlap = set(data.scope_ids or []) & set(existing.scope_ids)
                if overlap:
                    raise ValueError(f"组织 {list(overlap)} 已存在「{data.rule_name}」类型的规则（ID: {existing.id}），且适用机构有重叠，请修改已有规则的参数或适用范围")

        # 计算新规则优先级（默认排在末尾）
        count_stmt = select(func.count()).select_from(SchConstraint)
        count_result = await db.execute(count_stmt)
        default_priority = (count_result.scalar() or 0) + 1

        constraint = SchConstraint(
            rule_type=data.rule_type,
            rule_name=data.rule_name,
            params=data.params,
            priority=data.priority if data.priority > 0 else default_priority,
            scope_type=data.scope_type,
            scope_ids=data.scope_ids,
            enabled=data.enabled,
            is_preset=False,
        )
        db.add(constraint)
        await db.commit()
        await db.refresh(constraint)
        return constraint

    @staticmethod
    async def update_constraint(db: AsyncSession, constraint_id: int, data: ConstraintUpdate) -> SchConstraint:
        """更新约束规则"""
        constraint = await ConstraintService.get_constraint(db, constraint_id)
        if not constraint:
            raise ValueError("约束规则不存在")

        update_data = data.model_dump(exclude_unset=True)

        # 如果修改适用范围为全局，检查是否与已有全局规则冲突
        new_scope_type = update_data.get("scope_type", constraint.scope_type)
        if new_scope_type == "all":
            dup_count = await db.scalar(
                select(func.count()).where(
                    SchConstraint.rule_type == constraint.rule_type,
                    SchConstraint.scope_type == "all",
                    SchConstraint.id != constraint_id,
                )
            )
            if dup_count and dup_count > 0:
                raise ValueError(f"全局范围内已存在「{constraint.rule_type}」类型的规则，不能重复设置为全局，请修改已有规则的参数")


        for field, value in update_data.items():
            setattr(constraint, field, value)

        await db.commit()
        await db.refresh(constraint)
        return constraint

    @staticmethod
    async def delete_constraint(db: AsyncSession, constraint_id: int):
        """删除约束规则"""
        constraint = await ConstraintService.get_constraint(db, constraint_id)
        if not constraint:
            raise ValueError("约束规则不存在")

        # 预置规则不可删除，只能启用/禁用和修改参数
        if constraint.is_preset:
            raise ValueError("预置规则不可删除，只能启用/禁用和修改参数")

        await db.delete(constraint)
        await db.commit()

    @staticmethod
    async def toggle_constraint(db: AsyncSession, constraint_id: int) -> SchConstraint:
        """启用/禁用约束规则"""
        constraint = await ConstraintService.get_constraint(db, constraint_id)
        if not constraint:
            raise ValueError("约束规则不存在")

        constraint.enabled = not constraint.enabled
        await db.commit()
        await db.refresh(constraint)
        return constraint

    @staticmethod
    async def batch_update_priority(db: AsyncSession, data: BatchPriorityRequest):
        """批量更新优先级"""
        for item in data.items:
            stmt = select(SchConstraint).where(SchConstraint.id == item.id)
            result = await db.execute(stmt)
            constraint = result.scalars().first()
            if constraint:
                constraint.priority = item.priority
        await db.commit()
