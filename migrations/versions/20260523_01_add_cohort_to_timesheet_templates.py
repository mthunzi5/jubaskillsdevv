"""add cohort_id to timesheet templates

Revision ID: 20260523_01
Revises: 20260518_01
Create Date: 2026-05-23 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260523_01'
down_revision = '20260518_01'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('timesheet_templates'):
        columns = {col['name'] for col in inspector.get_columns('timesheet_templates')}
        if 'cohort_id' not in columns:
            op.add_column('timesheet_templates', sa.Column('cohort_id', sa.Integer(), nullable=True))

        indexes = {idx['name'] for idx in inspector.get_indexes('timesheet_templates')}
        if 'ix_timesheet_templates_cohort_id' not in indexes:
            op.create_index('ix_timesheet_templates_cohort_id', 'timesheet_templates', ['cohort_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('timesheet_templates'):
        indexes = {idx['name'] for idx in inspector.get_indexes('timesheet_templates')}
        if 'ix_timesheet_templates_cohort_id' in indexes:
            op.drop_index('ix_timesheet_templates_cohort_id', table_name='timesheet_templates')

        columns = {col['name'] for col in inspector.get_columns('timesheet_templates')}
        if 'cohort_id' in columns:
            op.drop_column('timesheet_templates', 'cohort_id')
