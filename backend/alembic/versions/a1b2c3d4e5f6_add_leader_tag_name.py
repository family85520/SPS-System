"""add leader_tag_name to shift_template

Revision ID: a1b2c3d4e5f6
Revises: f9f493e67b81
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f9f493e67b81'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sch_shift_templates',
                  sa.Column('leader_tag_name', sa.String(30), nullable=True,
                            comment="标识领导的身份标签名，默认'领导'"))


def downgrade():
    op.drop_column('sch_shift_templates', 'leader_tag_name')
