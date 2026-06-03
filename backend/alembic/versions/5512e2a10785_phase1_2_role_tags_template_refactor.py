"""phase1_2_role_tags_template_refactor

Revision ID: 5512e2a10785
Revises: ef57b8aee5d2
Create Date: 2026-05-24 12:29:25.159212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = '5512e2a10785'
down_revision: Union[str, None] = 'ef57b8aee5d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # Phase 1: 角色标识体系
    # ============================================================

    # 1.1 sys_role 新增 role_type 字段
    op.add_column(
        'sys_role',
        sa.Column(
            'role_type',
            sa.String(10),
            server_default='role',
            nullable=False,
            comment="角色类型: role=角色(有权限) tag=标识(仅标记人员)"
        )
    )

    # 1.2 新建 org_staff_role 关联表
    op.create_table(
        'org_staff_role',
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment="主键"
        ),
        sa.Column(
            'staff_id',
            sa.Integer(),
            sa.ForeignKey('org_staff.id', ondelete='CASCADE'),
            nullable=False,
            comment="人员ID"
        ),
        sa.Column(
            'role_id',
            sa.Integer(),
            sa.ForeignKey('sys_role.id', ondelete='CASCADE'),
            nullable=False,
            comment="标识角色ID"
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 创建索引
    op.create_index(
        'ix_org_staff_role_staff_id',
        'org_staff_role',
        ['staff_id']
    )
    op.create_index(
        'ix_org_staff_role_role_id',
        'org_staff_role',
        ['role_id']
    )

    # 创建唯一约束
    op.create_unique_constraint(
        'uq_staff_role_tag',
        'org_staff_role',
        ['staff_id', 'role_id']
    )

    # ============================================================
    # Phase 2: 班次模板重构
    # ============================================================

    # 2.1 sch_shift_template 新增字段
    template_columns = [
        (
            'allow_multi_template',
            sa.Boolean(),
            False,
            "是否允许本模板人员同日参与其他模板"
        ),
        (
            'leader_enabled',
            sa.Boolean(),
            False,
            "值班领导组开关"
        ),
        (
            'leader_count',
            sa.Integer(),
            1,
            "领导组每次选出人数"
        ),
        (
            'leader_use_tag',
            sa.Boolean(),
            True,
            "领导候选池为空时是否回退到标识人员"
        ),
        (
            'member_enabled',
            sa.Boolean(),
            True,
            "值班人员组开关"
        ),
        (
            'special_enabled',
            sa.Boolean(),
            False,
            "特殊人员组开关"
        ),
        (
            'special_count',
            sa.Integer(),
            1,
            "特殊组每次选出人数"
        ),
        (
            'special_exclude_from_member',
            sa.Boolean(),
            True,
            "特殊人员是否从值班人员池排除"
        ),
    ]

    for col_name, col_type, default, comment in template_columns:
        op.add_column(
            'sch_shift_template',
            sa.Column(
                col_name,
                col_type,
                server_default=str(default),
                nullable=False,
                comment=comment
            )
        )

    # 可空字段单独处理
    nullable_template_columns = [
        (
            'leader_rotation_frequency',
            sa.String(20),
            "领导组独立轮换频次，NULL则用整体频次"
        ),
        (
            'member_rotation_frequency',
            sa.String(20),
            "人员组独立轮换频次，NULL则用整体频次"
        ),
        (
            'special_rotation_frequency',
            sa.String(20),
            "特殊组独立轮换频次"
        ),
        (
            'special_pool',
            JSON(),
            "特殊人员候选ID列表"
        ),
        (
            'constraint_ids',
            JSON(),
            "关联约束规则ID列表，NULL则使用全部规则"
        ),
    ]

    for col_name, col_type, comment in nullable_template_columns:
        op.add_column(
            'sch_shift_template',
            sa.Column(
                col_name,
                col_type,
                nullable=True,
                comment=comment
            )
        )

    # 2.2 org_organization 新增字段
    op.add_column(
        'org_organization',
        sa.Column(
            'daily_max_scheduled_ratio',
            sa.Numeric(3, 2),
            nullable=True,
            comment="每日排班人数上限比例（如0.70=70%），NULL则使用全局默认"
        )
    )

    # 2.3 sys_config 新增配置项
    # 先检查表是否存在
    op.execute("""
        INSERT INTO sys_config (config_key, config_value, description)
        VALUES (
            'DAILY_MAX_SCHEDULED_RATIO',
            '0.7',
            '全局每日排班人数上限比例（0.7=70%的人每天排班）'
        )
        ON CONFLICT (config_key) DO NOTHING
    """)

    # 2.4 确保现有4个内置角色的 role_type 为 'role'
    op.execute("""
        UPDATE sys_role
        SET role_type = 'role'
        WHERE is_system = true AND (role_type IS NULL OR role_type = '')
    """)


def downgrade() -> None:
    # ============================================================
    # 回滚 Phase 2
    # ============================================================

    # 删除 sys_config 新增配置
    op.execute("""
        DELETE FROM sys_config
        WHERE config_key = 'DAILY_MAX_SCHEDULED_RATIO'
    """)

    # 删除 org_organization 新增字段
    op.drop_column('org_organization', 'daily_max_scheduled_ratio')

    # 删除 sch_shift_template 新增字段（按相反顺序）
    template_fields_to_drop = [
        'constraint_ids',
        'special_exclude_from_member',
        'special_pool',
        'special_count',
        'special_rotation_frequency',
        'special_enabled',
        'member_rotation_frequency',
        'member_enabled',
        'leader_use_tag',
        'leader_count',
        'leader_rotation_frequency',
        'leader_enabled',
        'allow_multi_template',
    ]

    for col_name in template_fields_to_drop:
        op.drop_column('sch_shift_template', col_name)

    # ============================================================
    # 回滚 Phase 1
    # ============================================================

    # 删除 org_staff_role 表
    op.drop_index('ix_org_staff_role_role_id', table_name='org_staff_role')
    op.drop_index('ix_org_staff_role_staff_id', table_name='org_staff_role')
    op.drop_constraint('uq_staff_role_tag', 'org_staff_role', type_='unique')
    op.drop_table('org_staff_role')

    # 删除 sys_role 新增字段
    op.drop_column('sys_role', 'role_type')
