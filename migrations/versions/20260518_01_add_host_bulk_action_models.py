"""add host bulk action models

Revision ID: 20260518_01
Revises: 20260517_02
Create Date: 2026-05-18 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260518_01'
down_revision = '20260517_02'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('timesheet_non_working_months'):
        op.create_table(
            'timesheet_non_working_months',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('host_company_id', sa.Integer(), nullable=False),
            sa.Column('cohort_id', sa.Integer(), nullable=True),
            sa.Column('intern_id', sa.Integer(), nullable=False),
            sa.Column('submission_month', sa.String(length=7), nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['cohort_id'], ['cohorts.id']),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['host_company_id'], ['host_companies.id']),
            sa.ForeignKeyConstraint(['intern_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('host_company_id', 'cohort_id', 'intern_id', 'submission_month', name='uq_non_working_month')
        )

    if not inspector.has_table('host_intern_monthly_feedback'):
        op.create_table(
            'host_intern_monthly_feedback',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('host_company_id', sa.Integer(), nullable=False),
            sa.Column('cohort_id', sa.Integer(), nullable=True),
            sa.Column('intern_id', sa.Integer(), nullable=False),
            sa.Column('submission_month', sa.String(length=7), nullable=False),
            sa.Column('attendance_rating', sa.Integer(), nullable=True),
            sa.Column('punctuality_rating', sa.Integer(), nullable=True),
            sa.Column('communication_rating', sa.Integer(), nullable=True),
            sa.Column('task_quality_rating', sa.Integer(), nullable=True),
            sa.Column('comments', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['cohort_id'], ['cohorts.id']),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['host_company_id'], ['host_companies.id']),
            sa.ForeignKeyConstraint(['intern_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('host_company_id', 'cohort_id', 'intern_id', 'submission_month', name='uq_host_feedback_month')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('host_intern_monthly_feedback'):
        op.drop_table('host_intern_monthly_feedback')

    if inspector.has_table('timesheet_non_working_months'):
        op.drop_table('timesheet_non_working_months')
