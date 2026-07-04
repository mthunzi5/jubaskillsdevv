"""add user termination columns

Revision ID: 20260704_01
Revises: 20260523_02
Create Date: 2026-07-04 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260704_01'
down_revision = '20260523_02'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('users'):
        columns = {column['name'] for column in inspector.get_columns('users')}
        if 'is_terminated' not in columns:
            op.add_column(
                'users',
                sa.Column('is_terminated', sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if 'termination_date' not in columns:
            op.add_column(
                'users',
                sa.Column('termination_date', sa.DateTime(), nullable=True)
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('users'):
        columns = {column['name'] for column in inspector.get_columns('users')}
        if 'termination_date' in columns:
            op.drop_column('users', 'termination_date')
        if 'is_terminated' in columns:
            op.drop_column('users', 'is_terminated')
