"""add_export_template

Revision ID: a1b2c3d4e5f6
Revises: 99a1b2c3d4e5
Create Date: 2026-06-01

新增自定义导出模板表
"""

from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '99a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exp_export_template',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('exp_export_template')
