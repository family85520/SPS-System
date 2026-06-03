"""remove_schedule_mode_rotation_frequency_rotation_group

Revision ID: 99a1b2c3d4e5
Revises: 5512e2a10785
Create Date: 2026-05-25

删除已废弃字段和表，将 leader/member/special_rotation_frequency 改为 NOT NULL。
迁移策略：先把旧 rotation_frequency 值继承到各自字段，再填默认值，最后删旧列。
"""

from alembic import op
import sqlalchemy as sa


revision = '99a1b2c3d4e5'
down_revision = '5512e2a10785'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 继承旧 rotation_frequency 值 → 各自的子频次字段（子字段为 NULL 时）
    op.execute("""
        UPDATE sch_shift_template
        SET leader_rotation_frequency = rotation_frequency
        WHERE leader_rotation_frequency IS NULL
    """)
    op.execute("""
        UPDATE sch_shift_template
        SET member_rotation_frequency = rotation_frequency
        WHERE member_rotation_frequency IS NULL
    """)
    op.execute("""
        UPDATE sch_shift_template
        SET special_rotation_frequency = rotation_frequency
        WHERE special_rotation_frequency IS NULL
    """)

    # 2. 补充仍为 NULL 的行（rotation_frequency 本身也是 NULL 的极端情况）
    op.execute("UPDATE sch_shift_template SET leader_rotation_frequency = 'week' WHERE leader_rotation_frequency IS NULL")
    op.execute("UPDATE sch_shift_template SET member_rotation_frequency = 'day' WHERE member_rotation_frequency IS NULL")
    op.execute("UPDATE sch_shift_template SET special_rotation_frequency = 'month' WHERE special_rotation_frequency IS NULL")

    # 3. 改为 NOT NULL 并设置独立默认值
    with op.batch_alter_table('sch_shift_template') as batch_op:
        batch_op.alter_column(
            'leader_rotation_frequency',
            existing_type=sa.String(20),
            nullable=False,
            server_default='week',
        )
        batch_op.alter_column(
            'member_rotation_frequency',
            existing_type=sa.String(20),
            nullable=False,
            server_default='day',
        )
        batch_op.alter_column(
            'special_rotation_frequency',
            existing_type=sa.String(20),
            nullable=False,
            server_default='month',
        )

    # 4. 删除已废弃列和表
    with op.batch_alter_table('sch_shift_template') as batch_op:
        batch_op.drop_column('schedule_mode')
        batch_op.drop_column('rotation_frequency')

    op.drop_table('sch_rotation_group')


def downgrade():
    # 恢复列
    with op.batch_alter_table('sch_shift_template') as batch_op:
        batch_op.add_column(
            sa.Column('rotation_frequency', sa.String(20), nullable=False, server_default='day')
        )
        batch_op.add_column(
            sa.Column('schedule_mode', sa.String(20), nullable=False, server_default='individual')
        )

    # 恢复轮换组表
    op.create_table(
        'sch_rotation_group',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shift_template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('staff_ids', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('rotation_unit', sa.String(20), nullable=False, server_default='month'),
        sa.Column('slot_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['shift_template_id'], ['sch_shift_template.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # 恢复频次字段为 nullable
    with op.batch_alter_table('sch_shift_template') as batch_op:
        batch_op.alter_column(
            'special_rotation_frequency',
            existing_type=sa.String(20),
            nullable=True,
            server_default=None,
        )
        batch_op.alter_column(
            'member_rotation_frequency',
            existing_type=sa.String(20),
            nullable=True,
            server_default=None,
        )
        batch_op.alter_column(
            'leader_rotation_frequency',
            existing_type=sa.String(20),
            nullable=True,
            server_default=None,
        )
