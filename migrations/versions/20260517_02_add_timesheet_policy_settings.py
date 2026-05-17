"""add timesheet policy settings table

Revision ID: 20260517_02
Revises: 20260517_01
Create Date: 2026-05-17 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260517_02'
down_revision = '20260517_01'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('timesheet_policy_settings'):
        op.create_table(
            'timesheet_policy_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('block_future_months', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('lock_before_month', sa.String(length=7), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('timesheet_policy_settings'):
        op.drop_table('timesheet_policy_settings')
